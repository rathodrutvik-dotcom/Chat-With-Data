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
    if not entries:
        return []

    clusters = {}
    for entry in entries:
        doc = entry["doc"]
        metadata = doc.metadata or {}
        source = metadata.get("source") or metadata.get("chunk_id") or "unknown-source"
        clusters.setdefault(source, []).append(entry)

    for cluster_entries in clusters.values():
        cluster_entries.sort(key=lambda e: e.get("rerank_score", e.get("score", 0)), reverse=True)

    sorted_clusters = sorted(
        clusters.values(),
        key=lambda cluster: cluster[0].get("rerank_score", cluster[0].get("score", 0)),
        reverse=True,
    )

    final_entries = []
    token_count = 0
    for cluster in sorted_clusters:
        for entry in cluster:
            if len(final_entries) >= max_chunks:
                break
            doc_tokens = count_tokens(entry["doc"])
            if token_count + doc_tokens > CONTEXT_TOKEN_BUDGET and final_entries:
                break
            final_entries.append(entry)
            token_count += doc_tokens
        if len(final_entries) >= max_chunks:
            break

    return final_entries


def format_context_with_metadata(entries):
    if not entries:
        return "No relevant context found in the uploaded documents."

    sections = []
    for idx, entry in enumerate(entries, start=1):
        doc = entry["doc"]
        metadata = doc.metadata or {}
        source = metadata.get("source") or metadata.get("chunk_id") or "unknown-source"
        chunk_id = metadata.get("chunk_id", "unknown-chunk")
        source_type = metadata.get("source_type", "chunk")
        summary_tag = metadata.get("summary_of_section")
        score = entry.get("rerank_score") or entry.get("score") or 0.0
        metadata_line = f"Source: {source} | Chunk: {chunk_id} | Type: {source_type} | Score: {score:.3f}"
        if summary_tag:
            metadata_line += f" | Summary: {summary_tag}"
        section_text = normalize_page_content(doc.page_content).strip()
        sections.append(f"Context {idx} ({metadata_line}):\n{section_text}")

    return "\n\n".join(sections)


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
]
