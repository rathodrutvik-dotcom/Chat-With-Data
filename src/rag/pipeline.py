import logging

import gradio as gr
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from config.settings import DENSE_CANDIDATE_K
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


def proceed_input(text, uploaded_files):
    """Main function to process text and uploaded files into a RAG chain."""
    try:
        saved_files, file_group_name = validate_and_save_files(uploaded_files)
        docs = load_docs(saved_files)
        logging.info("Loaded %s documents from files", len(docs))

        if text and text.strip():
            docs.append(Document(page_content=text))
            logging.info("Added user text to documents")

        if not docs:
            raise gr.Error("❌ No content to process. Please upload files or enter text.")

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
        context_text = format_context_with_metadata(relevant_context)
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
        return f"Error: {error_msg}"


__all__ = [
    "format_chat_history",
    "build_rag_chain",
    "retrieve_relevant_chunks",
    "proceed_input",
    "process_user_question",
]
