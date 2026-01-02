import os
import shutil
import datetime
import uuid
import pytz
import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import List
import gradio as gr


from langchain_groq import ChatGroq

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredExcelLoader,
    UnstructuredWordDocumentLoader,
)

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from sentence_transformers import CrossEncoder
from sklearn.feature_extraction.text import TfidfVectorizer



# ---------------------------------------
# CONFIG
# ---------------------------------------
IST = pytz.timezone("Asia/Kolkata")
LOG_FILE = f"{datetime.datetime.now(IST).strftime('%m_%d_%Y_%H_%M_%S')}.log"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "data"
EMBEDDING_STORE_DIR = PROJECT_ROOT / "embedding_store"
SYSTEM_PROMPT_DIR = Path(__file__).resolve().parent / "system_prompt"
LOG_PATH.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
EMBEDDING_STORE_DIR.mkdir(parents=True, exist_ok=True)

# Chunking heuristics
SLIDE_NEWLINE_RATIO_THRESHOLD = 0.15
SLIDE_WORD_THRESHOLD = 220
LONG_DOC_THRESHOLD = 4200
SUMMARY_MAX_CHARS = 520
SUMMARY_MIN_SECTION_WORDS = 80

# Retrieval Engineering
DENSE_CANDIDATE_K = 30
RERANK_TOP_K = 7
FINAL_CONTEXT_DOCS = 5
SIMILARITY_THRESHOLD = 0.82
DENSE_SCORE_WEIGHT = 0.7
SPARSE_SCORE_WEIGHT = 0.3
MAX_MULTI_QUERIES = 3
CONTEXT_TOKEN_BUDGET = 1400
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

_cross_encoder = None


def get_cross_encoder():
    """Lazily load the cross-encoder reranker model."""
    global _cross_encoder
    if _cross_encoder is None:
        _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _cross_encoder


@dataclass
class RagSession:
    rag_chain: object
    vectorstore: Chroma
    sparse_index: "SparseIndex"

logging.basicConfig(
    filename=str(LOG_PATH / LOG_FILE),
    format="[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ---------------------------------------
# Embedding Model
# ---------------------------------------
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
)


# ---------------------------------------
# Helpers: Loaders
# ---------------------------------------
def load_docs(files):
    """Auto-detect loader based on file extension and load documents."""
    logging.info("Loading documents")

    loaders = {
        ".pdf": PyPDFLoader,
        ".xlsx": UnstructuredExcelLoader,
        ".docx": UnstructuredWordDocumentLoader,
    }

    docs = []
    for file in files:
        ext = os.path.splitext(file)[1].lower()

        if ext not in loaders:
            raise gr.Error(f"❌ Unsupported file extension: {ext}")

        try:
            loader = loaders[ext](file)
            loaded_docs = loader.load()
            docs.extend(loaded_docs)
            logging.info(f"Loaded {len(loaded_docs)} pages/sheets from {file}")
        except Exception as e:
            logging.error(f"Error loading {file}: {str(e)}")
            raise gr.Error(f"❌ Error loading {os.path.basename(file)}: {str(e)}")

    return docs


# ---------------------------------------
# Text Splitter Helpers
# ---------------------------------------
def determine_split_params(doc):
    text = (doc.page_content or "").strip()
    word_count = len(text.split())
    if word_count == 0:
        return 400, 80

    newline_ratio = text.count("\n") / max(word_count, 1)

    if newline_ratio > SLIDE_NEWLINE_RATIO_THRESHOLD or word_count < SLIDE_WORD_THRESHOLD:
        return 450, 125

    if word_count > 1800:
        return 1500, 300

    return 1050, 200


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


# ---------------------------------------
# Text Splitter
# ---------------------------------------
def get_document_chunks(docs):
    chunked = []
    for doc in docs:
        chunk_size, chunk_overlap = determine_split_params(doc)
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        base_meta = dict(doc.metadata or {})
        source_prefix = base_meta.get("source") or f"chunk-{uuid.uuid4().hex[:8]}"

        for idx, chunk in enumerate(splitter.split_documents([doc]), start=1):
            metadata = dict(base_meta)
            metadata.update(chunk.metadata or {})
            metadata["chunk_id"] = metadata.get("chunk_id") or f"{source_prefix}-chunk-{idx}"
            metadata["chunk_index"] = idx
            metadata["source_type"] = metadata.get("source_type", "chunk")
            chunk.metadata = metadata
            chunked.append(chunk)

        chunked.extend(create_section_summaries(doc))

    logging.info(f"Split into {len(chunked)} chunks (including summaries)")
    return chunked


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


def get_last_message_by_role(chat_history, role):
    if not chat_history:
        return None
    for message in reversed(chat_history):
        if isinstance(message, dict) and message.get("role") == role:
            return message
    return None


def clean_chat_snippet(text, limit=CHAT_SNIPPET_MAX_CHARS):
    if not text:
        return ""
    if isinstance(text, dict):
        text = text.get("content") or text.get("text") or str(text)
    elif isinstance(text, list):
        text = " ".join(str(item) for item in text)
    else:
        text = str(text)

    snippet = " ".join(text.split())
    return snippet[:limit]


def normalize_page_content(content):
    if content is None:
        return ""
    if isinstance(content, list):
        normalized_parts = []
        for item in content:
            normalized_parts.append(" ".join(str(item).split()))
        return " ".join(normalized_parts)
    return str(content)


def rewrite_query(user_input, chat_history):
    trimmed = (user_input or "").strip()
    if not trimmed:
        return trimmed

    words = re.findall(r"\b[\w']+\b", trimmed.lower())
    contains_pronoun = any(word in FOLLOW_UP_PRONOUNS for word in words)
    last_user_message = get_last_message_by_role(chat_history, "user")
    last_assistant_message = get_last_message_by_role(chat_history, "assistant")

    snippets = []
    if contains_pronoun and last_user_message:
        snippet = clean_chat_snippet(last_user_message.get("content", ""))
        if snippet:
            snippets.append(f"Refer to previous user question: {snippet}")
    elif len(words) <= 3 and last_assistant_message:
        snippet = clean_chat_snippet(last_assistant_message.get("content", ""))
        if snippet:
            snippets.append(f"Context from assistant reply: {snippet}")

    rewritten = f"{trimmed} ({' | '.join(snippets)})" if snippets else trimmed
    logging.info("Rewritten query: %s", rewritten)
    return rewritten


def generate_query_variations(rewritten_query, chat_history):
    if not rewritten_query:
        return []

    variations = [rewritten_query]
    last_assistant_message = get_last_message_by_role(chat_history, "assistant")
    last_user_message = get_last_message_by_role(chat_history, "user")

    if last_assistant_message:
        snippet = clean_chat_snippet(last_assistant_message.get("content", ""))
        if snippet:
            variations.append(f"{rewritten_query} {snippet}")

    if last_user_message:
        snippet = clean_chat_snippet(last_user_message.get("content", ""))
        if snippet:
            variations.append(f"{rewritten_query} Refer to: {snippet}")

    unique_variations = []
    for variation in variations:
        if variation and variation not in unique_variations:
            unique_variations.append(variation)
        if len(unique_variations) >= MAX_MULTI_QUERIES:
            break
    return unique_variations


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


def retrieve_relevant_chunks(question: str, session: RagSession, chat_history=None):
    rewritten_query = rewrite_query(question, chat_history)
    queries = generate_query_variations(rewritten_query, chat_history) or [rewritten_query]
    logging.debug("Rewritten query: %s", rewritten_query)
    logging.debug("Query variations: %s", queries)

    dense_candidates = []
    for query in queries:
        hits = session.vectorstore.similarity_search_with_score(query, k=DENSE_CANDIDATE_K)
        dense_candidates.extend(hits)

    sparse_candidates = session.sparse_index.query(rewritten_query, top_k=DENSE_CANDIDATE_K)
    merged = merge_candidate_scores(dense_candidates, sparse_candidates)

    if not merged and dense_candidates:
        merged = [{"doc": doc, "score": score} for doc, score in dense_candidates]

    reranked = rerank_with_cross_encoder(rewritten_query, merged)
    unique_entries = filter_near_duplicates(reranked)
    context_entries = assemble_context_entries(unique_entries)
    logging.debug("Context entries selected: %s", len(context_entries))
    return context_entries


# ---------------------------------------
# Vector Store (Chroma)
# ---------------------------------------
def reset_embedding_store():
    """Remove any existing persisted embeddings to isolate a new upload."""
    if EMBEDDING_STORE_DIR.exists():
        shutil.rmtree(EMBEDDING_STORE_DIR)
    EMBEDDING_STORE_DIR.mkdir(parents=True, exist_ok=True)
    logging.info("Cleared previous embedding store")


def get_vector_store(splits, collection_name):
    """Create a fresh vector store tied to the current upload."""
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embedding_model,
        persist_directory=str(EMBEDDING_STORE_DIR),
        collection_name=collection_name,
    )
    logging.info("Vectorstore created for collection: %s", collection_name)
    return vectorstore



# ---------------------------------------
# System Prompt
# ---------------------------------------
def read_system_prompt(file_name):
    """Read system prompt from YAML file."""
    prompt_path = SYSTEM_PROMPT_DIR / file_name
    with open(prompt_path, "r") as f:
        content = f.read().strip()
        return content


# ---------------------------------------
# RAG Chain (Modern LCEL)
# ---------------------------------------
def format_chat_history(chat_history, limit=6):
    """Serialize the most recent chat turns (chronological) for grounding the LLM."""
    if not chat_history:
        return "None"

    filtered = [m for m in chat_history if isinstance(m, dict) and m.get("role") in {"user", "assistant"}]
    recent = filtered[-limit:]

    lines = []
    turn = 1
    for msg in recent:
        role = msg.get("role", "")
        content = msg.get("content", "")
        prefix = "User" if role == "user" else "Assistant" if role == "assistant" else role
        lines.append(f"Turn {turn} - {prefix}: {content}")
        turn += 1

    return "\n".join(lines) if lines else "None"


def build_rag_chain(system_prompt):
    """Build RAG chain with the LLM-only template."""
    logging.info("Building modern RAG pipeline")

    llm = ChatGroq(model="llama-3.3-70b-versatile")

    template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            (
                "human",
                "Question: {question}",
            ),
        ]
    )

    rag_chain = template | llm | StrOutputParser()
    return rag_chain


# ---------------------------------------
# File Save
# ---------------------------------------
def create_unique_filename():
    """Generate a unique filename with timestamp."""
    uid = uuid.uuid4()
    timestamp = datetime.datetime.now(IST).strftime("%d-%m-%Y-%H-%M-%S")
    return f"file-{uid}-{timestamp}"


def validate_and_save_files(uploaded_files):
    """Validate and save uploaded files to the data directory."""
    if not uploaded_files:
        raise gr.Error("⚠️ Please upload at least one file.")

    file_group_name = create_unique_filename()
    saved_files = []

    for idx, file in enumerate(uploaded_files, start=1):
        ext = os.path.splitext(file.name)[1].lower()

        if ext not in [".pdf", ".docx", ".xlsx"]:
            raise gr.Error(f"❌ Unsupported file type: {ext}. Only PDF, DOCX, XLSX are allowed.")

        save_path = DATA_DIR / f"{file_group_name}-{idx}{ext}"
        
        try:
            shutil.copyfile(file.name, str(save_path))
            saved_files.append(str(save_path))
            logging.info(f"Saved {file.name} → {save_path}")
        except Exception as e:
            logging.error(f"Error saving file {file.name}: {str(e)}")
            raise gr.Error(f"❌ Error saving file: {str(e)}")

    return saved_files, file_group_name


# ---------------------------------------
# MAIN RAG PROCESSOR
# ---------------------------------------
def proceed_input(text, uploaded_files):
    """Main function to process text and uploaded files into a RAG chain."""
    try:
        # Validate and save uploaded files
        saved_files, file_group_name = validate_and_save_files(uploaded_files)

        # Load documents from files
        docs = load_docs(saved_files)
        logging.info(f"Loaded {len(docs)} documents from files")

        # Add user free text as document if provided
        if text and text.strip():
            docs.append(Document(page_content=text))
            logging.info("Added user text to documents")

        if not docs:
            raise gr.Error("❌ No content to process. Please upload files or enter text.")

        # Process documents
        splits = get_document_chunks(docs)
        reset_embedding_store()
        vectorstore = get_vector_store(splits, collection_name=file_group_name)
        sparse_index = SparseIndex(splits)
        system_prompt = read_system_prompt("custom.yaml")

        logging.info("RAG chain built successfully")
        return RagSession(
            rag_chain=build_rag_chain(system_prompt),
            vectorstore=vectorstore,
            sparse_index=sparse_index,
        )
    
    except gr.Error:
        raise
    except Exception as e:
        logging.error(f"Error in proceed_input: {str(e)}")
        raise gr.Error(f"❌ Error processing documents: {str(e)}")


# ---------------------------------------
# ANSWER PROCESSING
# ---------------------------------------
def process_user_question(user_input, session: RagSession, chat_history=None):
    """Process user question and get answer from RAG chain."""
    try:
        # Ensure user_input is a string
        if isinstance(user_input, list):
            user_input = " ".join(str(item) for item in user_input)
        elif not isinstance(user_input, str):
            user_input = str(user_input)
        
        # Validate input
        if not user_input or not user_input.strip():
            return "Please enter a valid question."
        
        logging.info(f"User Q: {user_input}")
        relevant_context = retrieve_relevant_chunks(user_input, session, chat_history)
        context_text = format_context_with_metadata(relevant_context)
        history_text = format_chat_history(chat_history)
        payload = {
            "context": context_text,
            "history": history_text,
            "question": user_input,
        }
        answer = session.rag_chain.invoke(payload)
        logging.info(f"Answer generated successfully: {len(answer)} chars")
        return answer
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error processing question: {error_msg}", exc_info=True)
        
        # Provide more specific error messages
        if "replace" in error_msg:
            return "Error: Document formatting issue. Please reprocess your documents."
        elif "API" in error_msg or "Groq" in error_msg:
            return "Error: API connection issue. Please check your GROQ_API_KEY."
        else:
            return f"Error: {error_msg}"
