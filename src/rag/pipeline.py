import logging

import gradio as gr
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

from config.settings import (
    DENSE_CANDIDATE_K,
    USE_GROQ,
    USE_GEMINI,
    GROQ_MODEL,
    GEMINI_MODEL,
)
from ingestion.chunking import get_document_chunks
from ingestion.files import validate_and_save_files
from ingestion.loaders import load_docs
from models.session import RagSession
from prompts.system_prompt import read_system_prompt
from retrieval.query_rewrite import generate_query_variations, rewrite_query
from retrieval.ranking import (
    SparseIndex,
    assemble_context_entries,
    filter_near_duplicates,
    format_context_with_metadata,
    merge_candidate_scores,
    rerank_with_cross_encoder,
)
from vectorstore.chroma_store import get_vector_store, reset_embedding_store


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


def build_rag_chain(system_prompt, use_groq=None, use_gemini=None):
    """
    Build RAG chain with configurable LLM provider.
    
    Args:
        system_prompt: System prompt for the LLM
        use_groq: Boolean to enable Groq (defaults to USE_GROQ from settings)
        use_gemini: Boolean to enable Gemini (defaults to USE_GEMINI from settings)
    
    Returns:
        RAG chain with selected LLM
    """
    logging.info("Building modern RAG pipeline")
    
    # Use provided parameters or fall back to environment settings
    use_groq_flag = use_groq if use_groq is not None else USE_GROQ
    use_gemini_flag = use_gemini if use_gemini is not None else USE_GEMINI
    
    # Determine which LLM to use (priority: Gemini > Groq)
    llm = None
    
    if use_gemini_flag:
        try:
            logging.info(f"Initializing Gemini LLM with model: {GEMINI_MODEL}")
            llm = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                temperature=0.7,
                convert_system_message_to_human=True
            )
            logging.info("✅ Successfully initialized Gemini LLM")
        except Exception as e:
            logging.error(f"❌ Failed to initialize Gemini: {e}")
            if not use_groq_flag:
                raise gr.Error(f"Failed to initialize Gemini and Groq is disabled: {e}")
    
    if llm is None and use_groq_flag:
        try:
            logging.info(f"Initializing Groq LLM with model: {GROQ_MODEL}")
            llm = ChatGroq(model=GROQ_MODEL)
            logging.info("✅ Successfully initialized Groq LLM")
        except Exception as e:
            logging.error(f"❌ Failed to initialize Groq: {e}")
            raise gr.Error(f"Failed to initialize Groq LLM: {e}")
    
    if llm is None:
        error_msg = "No LLM provider enabled. Please set USE_GROQ=true or USE_GEMINI=true in .env"
        logging.error(error_msg)
        raise gr.Error(error_msg)

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


def proceed_input(uploaded_files, document_name: str = None):
    """Main function to process uploaded files into a RAG chain."""
    try:
        saved_files, collection_name, auto_document_name = validate_and_save_files(uploaded_files)
        docs = load_docs(saved_files)
        logging.info("Loaded %s documents from files", len(docs))

        if not docs:
            raise gr.Error("❌ No content to process. Please upload files.")

        splits = get_document_chunks(docs)
        # Don't reset - allow multiple sessions to coexist
        vectorstore = get_vector_store(splits, collection_name=collection_name)
        sparse_index = SparseIndex(splits)
        system_prompt = read_system_prompt("custom.yaml")

        # Use auto-generated name (ignore user input)
        doc_name = auto_document_name

        logging.info("RAG chain built successfully")
        rag_session = RagSession(
            rag_chain=build_rag_chain(system_prompt),
            vectorstore=vectorstore,
            sparse_index=sparse_index,
        )
        
        return rag_session, collection_name, doc_name

    except gr.Error:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        logging.error("Error in proceed_input: %s", str(exc))
        raise gr.Error(f"❌ Error processing documents: {str(exc)}") from exc


def process_user_question(user_input, session: RagSession, chat_history=None):
    """Process user question and get answer from RAG chain."""
    try:
        if isinstance(user_input, list):
            user_input = " ".join(str(item) for item in user_input)
        elif not isinstance(user_input, str):
            user_input = str(user_input)

        if not user_input or not user_input.strip():
            return "Please enter a valid question."

        logging.info("User Q: %s", user_input)
        relevant_context = retrieve_relevant_chunks(user_input, session, chat_history)
        logging.info("Number of context entries retrieved: %d", len(relevant_context))
        context_text = format_context_with_metadata(relevant_context)
        
        # Debug: Log the context being sent to LLM
        logging.info("=" * 80)
        logging.info("CONTEXT BEING SENT TO LLM:")
        logging.info(context_text)
        logging.info("=" * 80)
        history_text = format_chat_history(chat_history)
        payload = {
            "context": context_text,
            "history": history_text,
            "question": user_input,
        }
        answer = session.rag_chain.invoke(payload)
        logging.info("Answer generated successfully: %s chars", len(answer))
        return answer
    except Exception as exc:  # pylint: disable=broad-except
        error_msg = str(exc)
        logging.error("Error processing question: %s", error_msg, exc_info=True)

        if "replace" in error_msg:
            return "Error: Document formatting issue. Please reprocess your documents."
        if "API" in error_msg or "Groq" in error_msg:
            return "Error: API connection issue. Please check your GROQ_API_KEY."
        if "Gemini" in error_msg or "Google" in error_msg:
            return "Error: API connection issue. Please check your GEMINI_API_KEY."
        return f"Error: {error_msg}"


__all__ = [
    "format_chat_history",
    "build_rag_chain",
    "retrieve_relevant_chunks",
    "proceed_input",
    "process_user_question",
]
