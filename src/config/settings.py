import datetime
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytz
from langchain_huggingface import HuggingFaceEmbeddings

# Paths
IST = pytz.timezone("Asia/Kolkata")
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_FILE = f"{datetime.datetime.now(IST).strftime('%Y_%m_%d')}.log"  # Daily log file
LOG_PATH = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "data"
EMBEDDING_STORE_DIR = PROJECT_ROOT / "embedding_store"
SYSTEM_PROMPT_DIR = Path(__file__).resolve().parent.parent / "system_prompt"

LOG_PATH.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True) 
EMBEDDING_STORE_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging with rotation and both file + console output
log_format = "[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s"
log_file_path = LOG_PATH / LOG_FILE

# Create handlers
file_handler = RotatingFileHandler(
    log_file_path,
    maxBytes=10 * 1024 * 1024,  # 10MB per file
    backupCount=7,  # Keep 7 backup files (1 week of daily logs)
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(log_format))

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(log_format))

# Configure root logger with both handlers
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[file_handler, console_handler]
)

# Configure uvicorn loggers to use our handlers and prevent propagation
uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.handlers = [file_handler, console_handler]
uvicorn_logger.propagate = False  # Prevent propagation to root logger

uvicorn_error = logging.getLogger("uvicorn.error")
uvicorn_error.handlers = [file_handler, console_handler]
uvicorn_error.propagate = False  # Prevent propagation to root logger

uvicorn_access = logging.getLogger("uvicorn.access")
uvicorn_access.handlers = [file_handler, console_handler]
uvicorn_access.propagate = False  # Prevent propagation to root logger

logger = logging.getLogger(__name__)
logger.info(f"Logging configured - Daily log file: {LOG_FILE}")

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
CHAT_SNIPPET_MAX_CHARS = 160

CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# LLM Provider Configuration
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

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
    "CHAT_SNIPPET_MAX_CHARS",
    "CROSS_ENCODER_MODEL",
    "GEMINI_MODEL",
    "embedding_model",
]
