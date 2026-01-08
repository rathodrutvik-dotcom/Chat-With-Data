import datetime
import logging
import os
from pathlib import Path

import pytz
from langchain_huggingface import HuggingFaceEmbeddings

# Paths
IST = pytz.timezone("Asia/Kolkata")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = f"{datetime.datetime.now(IST).strftime('%m_%d_%Y_%H_%M_%S')}.log"
LOG_PATH = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "data"
EMBEDDING_STORE_DIR = PROJECT_ROOT / "embedding_store"
SYSTEM_PROMPT_DIR = Path(__file__).resolve().parent.parent / "system_prompt"

LOG_PATH.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
EMBEDDING_STORE_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_PATH / LOG_FILE),
    format="[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Chunking heuristics
SLIDE_NEWLINE_RATIO_THRESHOLD = 0.15
SLIDE_WORD_THRESHOLD = 220
LONG_DOC_THRESHOLD = 4200
SUMMARY_MAX_CHARS = 520
SUMMARY_MIN_SECTION_WORDS = 80

# Retrieval engineering
DENSE_CANDIDATE_K = 50  # Increased from 30 to get more candidates from all documents
RERANK_TOP_K = 12  # Increased from 7 to allow more diverse results
FINAL_CONTEXT_DOCS = 15  # Increased from 8 to cover multiple documents comprehensively
SIMILARITY_THRESHOLD = 0.75  # Reduced from 0.82 to allow more diverse chunks
DENSE_SCORE_WEIGHT = 0.7
SPARSE_SCORE_WEIGHT = 0.3
MAX_MULTI_QUERIES = 5  # Increased from 3 for more comprehensive querying
CONTEXT_TOKEN_BUDGET = 3500  # Increased from 2400 for multi-document context
FOLLOW_UP_PRONOUNS = {
    "it",
    "this",
    "that",
    "those",
    "they",
    "them",
    "he",
    "she",
    "him",
    "her",
    "his",
    "hers",
    "we",
    "us",
    "our",
    "ours",
    "you",
    "your",
    "yours",
}
CHAT_SNIPPET_MAX_CHARS = 160

CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# LLM Provider Configuration
USE_GROQ = os.getenv("USE_GROQ", "true").lower() == "true"
USE_GEMINI = os.getenv("USE_GEMINI", "false").lower() == "true"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")

# Embeddings
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
)

__all__ = [
    "IST",
    "PROJECT_ROOT",
    "LOG_FILE",
    "LOG_PATH",
    "DATA_DIR",
    "EMBEDDING_STORE_DIR",
    "SYSTEM_PROMPT_DIR",
    "SLIDE_NEWLINE_RATIO_THRESHOLD",
    "SLIDE_WORD_THRESHOLD",
    "LONG_DOC_THRESHOLD",
    "SUMMARY_MAX_CHARS",
    "SUMMARY_MIN_SECTION_WORDS",
    "DENSE_CANDIDATE_K",
    "RERANK_TOP_K",
    "FINAL_CONTEXT_DOCS",
    "SIMILARITY_THRESHOLD",
    "DENSE_SCORE_WEIGHT",
    "SPARSE_SCORE_WEIGHT",
    "MAX_MULTI_QUERIES",
    "CONTEXT_TOKEN_BUDGET",
    "FOLLOW_UP_PRONOUNS",
    "CHAT_SNIPPET_MAX_CHARS",
    "CROSS_ENCODER_MODEL",
    "USE_GROQ",
    "USE_GEMINI",
    "GROQ_MODEL",
    "GEMINI_MODEL",
    "embedding_model",
]
