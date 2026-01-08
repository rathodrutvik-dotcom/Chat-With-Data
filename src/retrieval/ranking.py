import logging
from difflib import SequenceMatcher
from typing import List

from langchain_core.documents import Document
from sentence_transformers import CrossEncoder
from sklearn.feature_extraction.text import TfidfVectorizer

from config.settings import (
    CONTEXT_TOKEN_BUDGET,
    CROSS_ENCODER_MODEL,
    DENSE_CANDIDATE_K,
    DENSE_SCORE_WEIGHT,
    FINAL_CONTEXT_DOCS,
    RERANK_TOP_K,
    SIMILARITY_THRESHOLD,
    SPARSE_SCORE_WEIGHT,
)

_cross_encoder = None


def get_cross_encoder():
    """Lazily load the cross-encoder reranker model."""
    global _cross_encoder
    if _cross_encoder is None:
        _cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL)
    return _cross_encoder


class SparseIndex:
    """A lightweight sparse text index backed by TF-IDF."""

    def __init__(self, documents: List[Document]):
        self.documents = documents or []
        self.texts = [(doc.page_content or "").strip() for doc in self.documents]
        self.vectorizer = None
        self.matrix = None

        try:
            if self.texts and any(self.texts):
                self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
                self.matrix = self.vectorizer.fit_transform(self.texts)
        except ValueError:
            self.vectorizer = None
            self.matrix = None

    def query(self, query_text: str, top_k: int = 40):
        if not self.vectorizer or self.matrix is None:
            return []

        query_vec = self.vectorizer.transform([query_text])
        scores = (self.matrix @ query_vec.T).toarray().ravel()
        ranked = [
            (self.documents[idx], float(score))
            for idx, score in enumerate(scores)
            if score > 0
        ]
        ranked.sort(key=lambda entry: entry[1], reverse=True)
        return ranked[:top_k]


def normalize_page_content(content):
    if content is None:
        return ""
    if isinstance(content, list):
        normalized_parts = [" ".join(str(item).split()) for item in content]
        return " ".join(normalized_parts)
    return str(content)


def normalize_scores(values):
    if not values:
        return []

    min_val = min(values)
    max_val = max(values)
    if abs(max_val - min_val) < 1e-9:
        return [1.0] * len(values)

    return [(value - min_val) / (max_val - min_val) for value in values]


def merge_candidate_scores(
    dense_candidates,
    sparse_candidates,
    dense_weight: float = DENSE_SCORE_WEIGHT,
    sparse_weight: float = SPARSE_SCORE_WEIGHT,
):
    aggregated = {}

    def chunk_key(document):
        return document.metadata.get("chunk_id") if document.metadata else str(id(document))

    for doc, score in dense_candidates:
        key = chunk_key(doc)
        entry = aggregated.setdefault(key, {"doc": doc, "dense_score": 0.0, "sparse_score": 0.0})
        entry["dense_score"] = max(entry["dense_score"], float(score))

    for doc, score in sparse_candidates:
        key = chunk_key(doc)
        entry = aggregated.setdefault(key, {"doc": doc, "dense_score": 0.0, "sparse_score": 0.0})
        entry["sparse_score"] = max(entry["sparse_score"], float(score))

    entries = list(aggregated.values())
    if not entries:
        return []

    dense_norm = normalize_scores([entry["dense_score"] for entry in entries])
    sparse_norm = normalize_scores([entry["sparse_score"] for entry in entries])

    combined = []
    for idx, entry in enumerate(entries):
        score = dense_weight * dense_norm[idx] + sparse_weight * sparse_norm[idx]
        combined.append({"doc": entry["doc"], "score": score})

    combined.sort(key=lambda item: item["score"], reverse=True)
    return combined


def rerank_with_cross_encoder(question, candidates, topo=RERANK_TOP_K):
    if not candidates:
        return []

    encoder = get_cross_encoder()
    limited = candidates[:DENSE_CANDIDATE_K]
    pairs = [(question, (entry["doc"].page_content or "")) for entry in limited]
    scores = encoder.predict(pairs)
    reranked = []
    for entry, rerank_score in zip(limited, scores):
        data = dict(entry)
        data["rerank_score"] = float(rerank_score)
        reranked.append(data)

    reranked.sort(key=lambda item: item["rerank_score"], reverse=True)
    return reranked[:topo]


def filter_near_duplicates(entries, similarity_threshold=SIMILARITY_THRESHOLD):
    filtered = []

    for entry in entries:
        doc = entry["doc"] if isinstance(entry, dict) else entry
        text = normalize_page_content(doc.page_content).strip()
        if not text:
            continue

        if any(
            SequenceMatcher(None, text, normalize_page_content(existing_entry["doc"].page_content).strip()).ratio()
            > similarity_threshold
            for existing_entry in filtered
        ):
            continue

        filtered.append(entry)

    return filtered


def count_tokens(item):
    text = normalize_page_content(item.page_content if hasattr(item, "page_content") else item)
    if not text:
        return 0
    return len(text.split())


def assemble_context_entries(entries, max_chunks=FINAL_CONTEXT_DOCS):
    """Assemble context entries with document diversity to ensure multi-document coverage.
    
    Uses round-robin selection across documents to ensure all source documents
    are represented in the final context, which is critical for multi-document queries.
    """
    if not entries:
        return []

    # Group by document (not just source/chunk)
    doc_clusters = {}
    for entry in entries:
        doc = entry["doc"]
        metadata = doc.metadata or {}
        # Use document_name for grouping to ensure different docs are treated separately
        doc_name = metadata.get("document_name") or metadata.get("source") or "unknown-source"
        doc_clusters.setdefault(doc_name, []).append(entry)

    # Sort entries within each document cluster by score
    for cluster_entries in doc_clusters.values():
        cluster_entries.sort(key=lambda e: e.get("rerank_score", e.get("score", 0)), reverse=True)

    # Sort document clusters by their best entry's score
    sorted_clusters = sorted(
        doc_clusters.items(),
        key=lambda item: item[1][0].get("rerank_score", item[1][0].get("score", 0)),
        reverse=True,
    )

    logging.info(f"Found {len(sorted_clusters)} unique documents in results")
    for doc_name, cluster in sorted_clusters:
        logging.info(f"  - {doc_name}: {len(cluster)} chunks")

    # Round-robin selection to ensure diversity across documents
    final_entries = []
    token_count = 0
    
    # Calculate minimum chunks per document to ensure fair representation
    min_chunks_per_doc = max(2, max_chunks // len(sorted_clusters)) if sorted_clusters else 1
    
    # First pass: Get at least min_chunks_per_doc from each document
    for doc_name, cluster in sorted_clusters:
        chunks_added = 0
        for entry in cluster:
            if len(final_entries) >= max_chunks:
                break
                
            doc_tokens = count_tokens(entry["doc"])
            if token_count + doc_tokens > CONTEXT_TOKEN_BUDGET and final_entries:
                continue
                
            final_entries.append(entry)
            token_count += doc_tokens
            chunks_added += 1
            
            if chunks_added >= min_chunks_per_doc:
                break
    
    # Second pass: Fill remaining slots with round-robin
    if len(final_entries) < max_chunks:
        cluster_iters = [iter(cluster[min_chunks_per_doc:]) for _, cluster in sorted_clusters]
        active_clusters = len(cluster_iters)
        
        while active_clusters > 0 and len(final_entries) < max_chunks:
            active_clusters = 0
            for cluster_iter in cluster_iters:
                try:
                    entry = next(cluster_iter)
                    active_clusters += 1
                    
                    if len(final_entries) >= max_chunks:
                        break
                        
                    doc_tokens = count_tokens(entry["doc"])
                    if token_count + doc_tokens > CONTEXT_TOKEN_BUDGET:
                        continue
                        
                    final_entries.append(entry)
                    token_count += doc_tokens
                    
                except StopIteration:
                    continue

    logging.info(f"Assembled {len(final_entries)} context entries from {len(sorted_clusters)} documents")
    return final_entries


def format_context_with_metadata(entries):
    """Format context entries with metadata for LLM consumption.
    
    Includes document source information for proper attribution in responses.
    Groups entries by document for better multi-document comprehension.
    """
    if not entries:
        return "No relevant context found in the uploaded documents."

    # Group entries by document for clearer presentation
    doc_groups = {}
    for entry in entries:
        doc = entry["doc"]
        metadata = doc.metadata or {}
        doc_name = metadata.get("document_name") or metadata.get("source") or "unknown"
        
        if doc_name not in doc_groups:
            doc_groups[doc_name] = []
        doc_groups[doc_name].append(entry)
    
    # Format with clear document grouping
    sections = []
    sections.append(f"=== INFORMATION FROM {len(doc_groups)} DOCUMENT(S) ===\\n")
    
    context_num = 1
    for doc_name, doc_entries in doc_groups.items():
        sections.append(f"--- DOCUMENT: {doc_name} ---")
        
        for entry in doc_entries:
            doc = entry["doc"]
            metadata = doc.metadata or {}
            
            chunk_id = metadata.get("chunk_id", "unknown-chunk")
            source_type = metadata.get("source_type", "chunk")
            summary_tag = metadata.get("summary_of_section")
            score = entry.get("rerank_score") or entry.get("score") or 0.0
            page = metadata.get("page", "")
            
            # Build metadata line
            metadata_parts = []
            if page:
                metadata_parts.append(f"Page: {page}")
            metadata_parts.extend([
                f"Chunk: {chunk_id}",
                f"Type: {source_type}",
                f"Relevance: {score:.3f}"
            ])
            if summary_tag:
                metadata_parts.append(f"Summary: {summary_tag}")
                
            metadata_line = " | ".join(metadata_parts)
            section_text = normalize_page_content(doc.page_content).strip()
            sections.append(f"Context {context_num} ({metadata_line}):\n{section_text}")
            context_num += 1
        
        sections.append("")  # Empty line between documents

    return "\\n".join(sections)


def extract_source_documents(entries) -> list:
    """Extract unique source document names from context entries.
    
    Args:
        entries: List of context entries with document metadata
        
    Returns:
        List of unique document names that were used as sources
    """
    if not entries:
        return []
    
    sources = []
    seen = set()
    
    for entry in entries:
        doc = entry.get("doc")
        if not doc:
            continue
            
        metadata = doc.metadata or {}
        doc_name = metadata.get("document_name") or metadata.get("source") or "unknown"
        
        if doc_name not in seen:
            seen.add(doc_name)
            sources.append(doc_name)
    
    return sources


__all__ = [
    "SparseIndex",
    "normalize_page_content",
    "normalize_scores",
    "merge_candidate_scores",
    "rerank_with_cross_encoder",
    "filter_near_duplicates",
    "count_tokens",
    "assemble_context_entries",
    "format_context_with_metadata",
    "extract_source_documents",
]
