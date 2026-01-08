import logging
import re
import uuid

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import (
    LONG_DOC_THRESHOLD,
    SLIDE_NEWLINE_RATIO_THRESHOLD,
    SLIDE_WORD_THRESHOLD,
    SUMMARY_MAX_CHARS,
    SUMMARY_MIN_SECTION_WORDS,
)
from ingestion.entity_extraction import enrich_chunk_metadata, inject_entity_prefixes


def determine_split_params(doc):
    text = (doc.page_content or "").strip()
    word_count = len(text.split())
    if word_count == 0:
        return 400, 100

    newline_ratio = text.count("\n") / max(word_count, 1)

    if newline_ratio > SLIDE_NEWLINE_RATIO_THRESHOLD or word_count < SLIDE_WORD_THRESHOLD:
        return 450, 150

    if word_count > 1800:
        return 1500, 400

    # Increased overlap for better context preservation
    return 1050, 250


def summarize_section(section_text):
    cleaned = " ".join(section_text.split())
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", cleaned) if s]
    if not sentences:
        return cleaned[:SUMMARY_MAX_CHARS]

    summary_parts = []
    length = 0
    for sent in sentences:
        if length + len(sent) + 1 > SUMMARY_MAX_CHARS:
            break
        summary_parts.append(sent)
        length += len(sent) + 1

    summary = " ".join(summary_parts).strip()
    return summary or cleaned[:SUMMARY_MAX_CHARS]


def create_section_summaries(doc):
    text = (doc.page_content or "").strip()
    if len(text) < LONG_DOC_THRESHOLD:
        return []

    sections = [sec.strip() for sec in re.split(r"\n{2,}", text) if sec.strip()]
    summary_nodes = []
    base_meta = dict(doc.metadata or {})
    source_prefix = base_meta.get("source") or f"section-{uuid.uuid4().hex[:8]}"

    for idx, section in enumerate(sections, start=1):
        if len(section.split()) < SUMMARY_MIN_SECTION_WORDS:
            continue

        summary_text = summarize_section(section)
        if not summary_text:
            continue

        metadata = dict(base_meta)
        metadata.setdefault("source", base_meta.get("source"))
        metadata["summary_of_section"] = f"section_{idx}"
        metadata["is_summary"] = True
        metadata["chunk_id"] = metadata.get("chunk_id") or f"{source_prefix}-summary-{idx}"
        metadata["source_type"] = metadata.get("source_type", "summary")

        summary_nodes.append(Document(page_content=summary_text, metadata=metadata))

    return summary_nodes


def get_document_chunks(docs):
    chunked = []
    for doc in docs:
        chunk_size, chunk_overlap = determine_split_params(doc)
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        base_meta = dict(doc.metadata or {})
        source_prefix = base_meta.get("source") or f"chunk-{uuid.uuid4().hex[:8]}"
        
        # Store parent document info for context
        parent_doc_name = base_meta.get("document_name") or base_meta.get("source")
        parent_doc_text = (doc.page_content or "").strip()
        parent_doc_preview = parent_doc_text[:500] if parent_doc_text else ""

        for idx, chunk in enumerate(splitter.split_documents([doc]), start=1):
            metadata = dict(base_meta)
            metadata.update(chunk.metadata or {})
            metadata["chunk_id"] = metadata.get("chunk_id") or f"{source_prefix}-chunk-{idx}"
            metadata["chunk_index"] = idx
            metadata["source_type"] = metadata.get("source_type", "chunk")
            metadata["parent_document"] = parent_doc_name
            metadata["parent_preview"] = parent_doc_preview  # Context from parent doc
            
            # Enrich metadata with extracted entities for better filtering and counting
            chunk_text = chunk.page_content or ""
            metadata = enrich_chunk_metadata(chunk_text, metadata)
            
            # Inject entity prefixes into chunk content for better retrieval
            enhanced_content = inject_entity_prefixes(chunk_text, metadata)
            chunk.page_content = enhanced_content
            
            chunk.metadata = metadata
            chunked.append(chunk)

        chunked.extend(create_section_summaries(doc))

    logging.info("Split into %s chunks (including summaries)", len(chunked))
    return chunked


__all__ = [
    "determine_split_params",
    "summarize_section",
    "create_section_summaries",
    "get_document_chunks",
]
