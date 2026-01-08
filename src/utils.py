"""Compatibility shim that re-exports the refactored modules.

The original project imported functions directly from utils.py. After
modularization, this file now acts as a thin facade to preserve the
public surface while delegating to the new, smaller modules.
"""

from config.settings import (  # noqa: F401
    CHAT_SNIPPET_MAX_CHARS,
    CONTEXT_TOKEN_BUDGET,
    CROSS_ENCODER_MODEL,
    DATA_DIR,
    DENSE_CANDIDATE_K,
    DENSE_SCORE_WEIGHT,
    EMBEDDING_STORE_DIR,
    FINAL_CONTEXT_DOCS,
    FOLLOW_UP_PRONOUNS,
    IST,
    LOG_FILE,
    LOG_PATH,
    LONG_DOC_THRESHOLD,
    MAX_MULTI_QUERIES,
    PROJECT_ROOT,
    RERANK_TOP_K,
    SIMILARITY_THRESHOLD,
    SLIDE_NEWLINE_RATIO_THRESHOLD,
    SLIDE_WORD_THRESHOLD,
    SPARSE_SCORE_WEIGHT,
    SUMMARY_MAX_CHARS,
    SUMMARY_MIN_SECTION_WORDS,
    SYSTEM_PROMPT_DIR,
    embedding_model,
)
from ingestion.chunking import (  # noqa: F401
    create_section_summaries,
    determine_split_params,
    get_document_chunks,
    summarize_section,
)
from ingestion.files import create_unique_filename, validate_and_save_files  # noqa: F401
from ingestion.loaders import load_docs  # noqa: F401
from models.session import RagSession, PipelineResult  # noqa: F401
from prompts.system_prompt import read_system_prompt  # noqa: F401
from rag.pipeline import (  # noqa: F401
    build_rag_chain,
    format_chat_history,
    process_user_question,
    proceed_input,
    retrieve_relevant_chunks,
)
from retrieval.query_rewrite import (  # noqa: F401
    clean_chat_snippet,
    generate_query_variations,
    get_last_message_by_role,
    rewrite_query,
)
from retrieval.ranking import (  # noqa: F401
    SparseIndex,
    assemble_context_entries,
    count_tokens,
    filter_near_duplicates,
    format_context_with_metadata,
    merge_candidate_scores,
    normalize_page_content,
    normalize_scores,
    rerank_with_cross_encoder,
)
from vectorstore.chroma_store import (  # noqa: F401
    get_chroma_settings,
    get_session_store_dir,
    get_vector_store,
    reset_embedding_store,
)

__all__ = [
    # Settings exports
    "CHAT_SNIPPET_MAX_CHARS",
    "CONTEXT_TOKEN_BUDGET",
    "CROSS_ENCODER_MODEL",
    "DATA_DIR",
    "DENSE_CANDIDATE_K",
    "DENSE_SCORE_WEIGHT",
    "EMBEDDING_STORE_DIR",
    "FINAL_CONTEXT_DOCS",
    "FOLLOW_UP_PRONOUNS",
    "IST",
    "LOG_FILE",
    "LOG_PATH",
    "LONG_DOC_THRESHOLD",
    "MAX_MULTI_QUERIES",
    "PROJECT_ROOT",
    "RERANK_TOP_K",
    "SIMILARITY_THRESHOLD",
    "SLIDE_NEWLINE_RATIO_THRESHOLD",
    "SLIDE_WORD_THRESHOLD",
    "SPARSE_SCORE_WEIGHT",
    "SUMMARY_MAX_CHARS",
    "SUMMARY_MIN_SECTION_WORDS",
    "SYSTEM_PROMPT_DIR",
    "embedding_model",
    # Ingestion
    "create_section_summaries",
    "determine_split_params",
    "get_document_chunks",
    "summarize_section",
    "create_unique_filename",
    "validate_and_save_files",
    "load_docs",
    # Models
    "RagSession",
    "PipelineResult",
    # Prompts
    "read_system_prompt",
    # RAG pipeline
    "build_rag_chain",
    "format_chat_history",
    "process_user_question",
    "proceed_input",
    "retrieve_relevant_chunks",
    # Retrieval helpers
    "clean_chat_snippet",
    "generate_query_variations",
    "get_last_message_by_role",
    "rewrite_query",
    "SparseIndex",
    "assemble_context_entries",
    "count_tokens",
    "filter_near_duplicates",
    "format_context_with_metadata",
    "merge_candidate_scores",
    "normalize_page_content",
    "normalize_scores",
    "rerank_with_cross_encoder",
    # Vector store utilities
    "get_chroma_settings",
    "get_session_store_dir",
    "get_vector_store",
    "reset_embedding_store",
]
