"""
Builds the RAG pipeline with Gemini LLM provider.
Handles document processing, retrieval strategies, and user query processing.
"""


import logging
import tempfile
import shutil
from pathlib import Path

import gradio as gr
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from config.settings import (
    GEMINI_MODEL,
)
from ingestion.chunking import get_document_chunks
from ingestion.files import validate_and_save_files
from ingestion.loaders import load_docs
from models.session import RagSession, PipelineResult
from prompts.system_prompt import read_system_prompt
from retrieval.query_rewrite import generate_query_variations, rewrite_query
from retrieval.question_decomposition import (
    analyze_query,
    extract_document_filter_from_question,
    synthesize_answers,
)
from retrieval.answer_validation import (
    validate_answer_with_llm,
    append_validation_warning,
)
from retrieval.ranking import (
    SparseIndex,
    assemble_context_entries,
    filter_near_duplicates,
    format_context_with_metadata,
    merge_candidate_scores,
    rerank_with_cross_encoder,
    extract_source_documents,
)
from vectorstore.chroma_store import get_vector_store, get_all_chunks_by_metadata


def determine_retrieval_strategy(question: str, strategy_hint: str = None, metadata_filters: dict = None):
    """
    Determine retrieval strategy based on LLM analysis.
    Dynamic approach - no hardcoded keywords, fully trusts LLM analysis.
    """
    # Trust the LLM analysis completely
    mode = strategy_hint or 'semantic'

    if mode == 'exhaustive':
        logging.info("Retrieval strategy: EXHAUSTIVE (LLM determined)")

        # Use filters provided by LLM analysis
        final_filters = metadata_filters or {}

        return {
            'mode': 'exhaustive',
            'k': None,
            'metadata_filter': final_filters
        }
    elif mode == 'conversational':
        logging.info("Retrieval strategy: CONVERSATIONAL (No retrieval)")
        return {
            'mode': 'conversational',
            'k': 0,
            'metadata_filter': None
        }
    else:
        # Semantic Mode - use standard k value
        k_value = 50

        logging.info("Retrieval strategy: SEMANTIC (k=%d)", k_value)
        return {
            'mode': 'semantic',
            'k': k_value,
            'metadata_filter': None
        }


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
    """
    Build RAG chain with Gemini LLM provider.

    Args:
        system_prompt: System prompt for the LLM

    Returns:
        RAG chain with Gemini LLM
    """
    logging.info("Building modern RAG pipeline")

    # Initialize Gemini LLM
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
        raise gr.Error(f"Failed to initialize Gemini LLM: {e}")

    template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            (
                "human",
                # Include history in the prompt template to support conversational flow
                "Conversation History:\n{history}\n\nContext from Documents:\n{context}\n\nQuestion: {question}",
            ),
        ]
    )

    rag_chain = template | llm | StrOutputParser()
    return rag_chain


def retrieve_relevant_chunks(user_input, session: RagSession, chat_history=None, document_filter=None, strategy_hint=None, metadata_filters=None, question_type="general"):
    """
    Retrieves the most relevant chunks based on query type and adaptive strategy.

    Args:
        user_input: The user's query
        session: RAG session with vector store and sparse index
        chat_history: Previous conversation history
        document_filter: Optional document name to filter by
        strategy_hint: Suggested retrieval strategy (exhaustive/semantic)
        metadata_filters: Additional metadata filters
        question_type: Type of question (count/list/timeline/general)

    Returns:
        Tuple of (context_entries, resolved_query) where resolved_query is the
        context-resolved version of user_input (for semantic mode) or user_input itself
    """
    print(f"--- DEBUG: START RETRIEVAL ---", flush=True)
    print(f"Query: '{user_input}'", flush=True)

    # Step 0: Determine retrieval strategy
    strategy = determine_retrieval_strategy(user_input, strategy_hint, metadata_filters)
    
    if strategy['mode'] == 'conversational':
        print("--- DEBUG: RETRIEVAL STRATEGY: CONVERSATIONAL ---", flush=True)
        print("Skipping retrieval for conversational input.", flush=True)
        # Return empty context and original input
        return [], user_input

    if strategy['mode'] == 'exhaustive':
        # EXHAUSTIVE MODE: Retrieve all matching chunks without TopK limit
        print("--- DEBUG: RETRIEVAL STRATEGY: EXHAUSTIVE ---", flush=True)
        print("Optimization: Skipping query rewrite for comprehensive search.", flush=True)
        logging.info("Using EXHAUSTIVE retrieval mode for counting/enumeration query")
        logging.info("Document filter: %s, Metadata filter: %s", document_filter, strategy['metadata_filter'])

        exhaustive_results = get_all_chunks_by_metadata(
            session.vectorstore,
            metadata_filter=strategy['metadata_filter'],
            document_filter=document_filter
        )

        # Convert to candidate format
        candidates = []
        for doc, score in exhaustive_results:
            candidates.append({
                "doc": doc,
                "score": score,
                "source": "exhaustive"
            })

        logging.info("Exhaustive retrieval: %d candidates", len(candidates))

        # Apply document filter in post-processing (more reliable than ChromaDB filtering)
        if document_filter:
            # Collect all unique document names for debugging
            all_doc_names = set(c["doc"].metadata.get("document_name", "") for c in candidates)
            logging.info("Available documents before filtering: %s", list(all_doc_names))

            filtered = []
            doc_filter_lower = document_filter.lower()
            # Remove file extension and common separators for flexible matching
            doc_filter_base = doc_filter_lower.replace('.pdf', '').replace('.docx', '').replace('.xlsx', '')
            doc_filter_base = doc_filter_base.replace('_', ' ').replace('-', ' ')

            for candidate in candidates:
                doc_name = candidate["doc"].metadata.get("document_name", "")
                doc_name_lower = doc_name.lower()
                doc_name_base = doc_name_lower.replace('.pdf', '').replace('.docx', '').replace('.xlsx', '')
                doc_name_base = doc_name_base.replace('_', ' ').replace('-', ' ')

                # Multiple matching strategies
                matched = False
                if doc_filter_lower == doc_name_lower:
                    matched = True
                elif doc_filter_base == doc_name_base:
                    matched = True
                elif doc_filter_lower in doc_name_lower:
                    matched = True
                elif doc_name_lower in doc_filter_lower:
                    matched = True
                elif doc_filter_base and doc_name_base and (
                    doc_filter_base in doc_name_base or doc_name_base in doc_filter_base
                ):
                    matched = True

                if matched:
                    filtered.append(candidate)
                else:
                    logging.debug("Filtered out: %s (looking for: %s)", doc_name, document_filter)

            logging.info("After document filter '%s': %d candidates (from %d total)",
                         document_filter, len(filtered), len(candidates))

            if len(filtered) == 0:
                logging.warning("⚠️ Document filter '%s' matched 0 documents!", document_filter)
                logging.warning("⚠️ Available documents: %s", list(all_doc_names))
                logging.warning("⚠️ Proceeding WITHOUT document filter to get all results")
                # Don't filter - return all candidates to avoid empty results
                filtered = candidates

            candidates = filtered

        # For exhaustive mode, skip reranking to preserve all results
        # Use higher threshold to keep more diverse content
        unique_entries = filter_near_duplicates(candidates, similarity_threshold=0.90)

        # For exhaustive mode, bypass normal limits to get ALL relevant content
        context_entries = assemble_context_entries(unique_entries, max_chunks=100, exhaustive_mode=True, question_type=question_type)

        logging.info("Exhaustive mode - Final context entries: %d", len(context_entries))
        if len(context_entries) == 0:
            logging.warning("⚠️ Exhaustive retrieval returned 0 results! Check metadata and filters.")
        return context_entries, user_input  # Return original query for exhaustive mode

    else:
        # SEMANTIC MODE: Use TopK with query variations
        print(f"--- DEBUG: RETRIEVAL STRATEGY: SEMANTIC (k={strategy['k']}) ---", flush=True)
        logging.info("Using SEMANTIC retrieval mode with k=%d", strategy['k'])
        retrieval_k = strategy['k']  # Use adaptive k value

        rewritten_query = rewrite_query(user_input, chat_history)
        print(f"Rewritten Query: '{rewritten_query}'", flush=True)

        queries = generate_query_variations(rewritten_query, chat_history) or [rewritten_query]
        logging.info("Rewritten query: %s", rewritten_query)
        logging.info("Generated %d query variations for comprehensive retrieval", len(queries))

        # Collect dense candidates from all query variations
        dense_candidates = []
        dense_docs_seen = set()

        for query in queries:
            # If document filter is specified, apply it during retrieval
            if document_filter:
                hits = session.vectorstore.similarity_search_with_score(
                    query,
                    k=retrieval_k,
                    filter={"document_name": document_filter}
                )
            else:
                hits = session.vectorstore.similarity_search_with_score(query, k=retrieval_k)

            for doc, score in hits:
                doc_id = id(doc)
                if doc_id not in dense_docs_seen:
                    # Apply document filter if specified (for vectorstores that don't support native filtering)
                    if document_filter:
                        doc_name = doc.metadata.get("document_name", "")
                        if document_filter.lower() not in doc_name.lower():
                            continue

                    dense_candidates.append((doc, score))
                    dense_docs_seen.add(doc_id)

        logging.info("Collected %d unique dense candidates from %d queries", len(dense_candidates), len(queries))

        # Get sparse candidates
        sparse_candidates = session.sparse_index.query(rewritten_query, top_k=retrieval_k)

        # Apply document filter to sparse candidates
        if document_filter:
            sparse_candidates = [
                (doc, score) for doc, score in sparse_candidates
                if document_filter.lower() in doc.metadata.get("document_name", "").lower()
            ]

        logging.info("Collected %d sparse candidates", len(sparse_candidates))

        # Merge and score
        merged = merge_candidate_scores(dense_candidates, sparse_candidates)
        logging.info("Merged candidates: %d", len(merged))

        if not merged and dense_candidates:
            merged = [{"doc": doc, "score": score} for doc, score in dense_candidates]

        # Rerank with cross-encoder
        reranked = rerank_with_cross_encoder(rewritten_query, merged)
        logging.info("Reranked to top %d candidates", len(reranked))

        # Filter duplicates
        unique_entries = filter_near_duplicates(reranked)
        logging.info("After deduplication: %d unique entries", len(unique_entries))
        
        # Force include chunk-0 for name/address queries
        if any(keyword in user_input.lower() for keyword in ['name', 'address', 'email', 'phone', 'contact']):
            logging.info("Detected name/address query - forcing inclusion of early chunks")
            # Get all available chunks from vectorstore to find chunk-0
            all_chunks = session.vectorstore.get()
            if all_chunks and 'ids' in all_chunks and 'documents' in all_chunks and 'metadatas' in all_chunks:
                for i, metadata in enumerate(all_chunks['metadatas']):
                    chunk_id = metadata.get('chunk_id', '')
                    # Look for chunk-0 or chunk-1 from resume or relevant documents
                    if 'chunk-0' in chunk_id or 'chunk_0' in chunk_id:
                        # Check if this chunk is already in unique_entries
                        already_included = any(
                            entry["doc"].metadata.get("chunk_id") == chunk_id 
                            for entry in unique_entries
                        )
                        if not already_included:
                            # Create document and add to unique_entries
                            from langchain_core.documents import Document
                            early_chunk_doc = Document(
                                page_content=all_chunks['documents'][i],
                                metadata=metadata
                            )
                            unique_entries.insert(0, {
                                "doc": early_chunk_doc,
                                "score": 1.0,  # High score to ensure inclusion
                                "rerank_score": 1.0
                            })
                            logging.info("Force-added %s to context for name/address query", chunk_id)

    # Assemble context with document diversity - pass question_type for smarter selection
    context_entries = assemble_context_entries(unique_entries, question_type=question_type)
    logging.info("Final context entries selected: %d", len(context_entries))

    # Log document distribution AND detailed content preview
    doc_distribution = {}
    print("--- DEBUG: SELECTED CONTEXT CHUNKS ---", flush=True)
    for i, entry in enumerate(context_entries):
        doc_name = entry["doc"].metadata.get("document_name", "unknown")
        doc_distribution[doc_name] = doc_distribution.get(doc_name, 0) + 1
        content_snippet = entry["doc"].page_content[:100].replace('\n', ' ')
        print(f"Chunk {i + 1}: Doc='{doc_name}', Score={entry.get('score', 'N/A')}, Content='{content_snippet} ...'", flush=True)

    print(f"Document distribution in context: {doc_distribution}", flush=True)
    print("--- DEBUG: END RETRIEVAL ---", flush=True)

    return context_entries, rewritten_query  # Return rewritten query for LLM


def proceed_input(uploaded_files, document_name: str = None):
    """Main function to process uploaded files into a RAG chain."""
    try:
        # Unpack original filenames as well
        saved_files, collection_name, auto_document_name, original_filenames = validate_and_save_files(uploaded_files)

        # Pass original filenames to loader
        docs = load_docs(saved_files, original_filenames)
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

        return PipelineResult(
            rag_session=rag_session,
            collection_name=collection_name,
            document_name=doc_name,
            original_filenames=original_filenames
        )

    except gr.Error:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        logging.error("Error in proceed_input: %s", str(exc))
        raise gr.Error(f"❌ Error processing documents: {str(exc)}") from exc


def process_user_question(user_input, session: RagSession, chat_history=None):
    """Process user question and get answer from RAG chain.

    Supports multi-intent question decomposition for comprehensive answers.

    Returns:
        Dictionary containing:
        - answer: The text response
        - sources: List of source documents used
    """
    try:
        if isinstance(user_input, list):
            user_input = " ".join(str(item) for item in user_input)
        elif not isinstance(user_input, str):
            user_input = str(user_input)

        if not user_input or not user_input.strip():
            return {"answer": "Please enter a valid question.", "sources": []}

        print("----- DEBUG: START QUERY PROCESSING -----", flush=True)
        print(f"User Q: {user_input}", flush=True)

        # Get available documents for context-aware analysis
        available_docs = None
        try:
            # Get list of unique documents in the vector store
            if session and session.vectorstore:
                all_docs = session.vectorstore.get()
                if all_docs and 'metadatas' in all_docs:
                    doc_names = set()
                    for metadata in all_docs['metadatas']:
                        if metadata and 'document_name' in metadata:
                            doc_names.add(metadata['document_name'])
                    available_docs = list(doc_names) if doc_names else None
                    if available_docs:
                        logging.info("Available documents for analysis: %s", available_docs)
        except Exception as e:
            logging.warning(f"Could not retrieve available documents: {e}")

        # Always use LLM to analyze query - this is the primary path
        # LLM determines strategy, filters, and multi-intent decomposition
        
        # OPTIMIZATION: Check for obvious conversational inputs to skip LLM analysis
        conversational_triggers = {
            "hi", "hello", "hey", "greetings", 
            "thanks", "thank you", "thx", "thanks!", "thank you!", 
            "ok", "okay", "cool", "great", "perfect", "awesome",
            "bye", "goodbye", "help"
        }
        
        # Phrases that indicate conversation even if sentence is longer
        conversational_prefixes = [
            "my name is", "call me", "i am chat", "i'm chat", "nice to meet",
            "what is my name", "who am i", "do you know my name", "do you remember me",
            "say my name"
        ]
        
        cleaned_input = user_input.lower().strip("!.,? ")
        
        is_conversational = False
        if cleaned_input in conversational_triggers:
            is_conversational = True
        elif len(cleaned_input.split()) <= 3 and any(trigger == cleaned_input for trigger in conversational_triggers):
            is_conversational = True
        elif any(cleaned_input.startswith(prefix) for prefix in conversational_prefixes):
             is_conversational = True
            
        if is_conversational:
            logging.info("⚡ Heuristic: Detected fast conversational input: '%s'", user_input)
            sub_questions = [{
                "question": user_input, 
                "type": "chat", 
                "strategy": "conversational", 
                "filters": {}
            }]
        else:
            sub_questions = analyze_query(user_input, available_documents=available_docs, chat_history=chat_history)

        # Check for explicit document filter in the question
        doc_filter = extract_document_filter_from_question(user_input)
        if doc_filter:
            logging.info("Detected document filter: %s", doc_filter)

        if len(sub_questions) > 1:
            print(f"--- DEBUG: MULTI-INTENT DETECTED ---", flush=True)
            print(f"Decomposed into {len(sub_questions)} sub-questions: {[sq['question'] for sq in sub_questions]}", flush=True)

        if len(sub_questions) > 1:
            logging.info("Processing %d sub-questions separately", len(sub_questions))

            # OPTIMIZATION: Group sub-questions that will likely retrieve same chunks
            # If all sub-questions are semantic and about the same entity, process together
            all_semantic = all(sq.get("strategy", "semantic") == "semantic" for sq in sub_questions)

            if all_semantic and len(sub_questions) <= 3:
                # Check if questions are about same entity (share significant words)
                question_words = [set(sq["question"].lower().split()) for sq in sub_questions]
                if len(question_words) >= 2:
                    common_words = question_words[0].intersection(*question_words[1:])
                    # If they share significant words, likely about same entity
                    significant_common = common_words - {"the", "a", "an", "of", "is", "what", "how", "when", "where", "who"}

                    if len(significant_common) >= 2:
                        # Combine into single question for efficiency
                        combined_question = user_input  # Use original multi-part question
                        logging.info("OPTIMIZATION: Combining related sub-questions into single retrieval")
                        print(f"--- DEBUG: OPTIMIZATION APPLIED ---", flush=True)
                        print(f"Detected related sub-questions about same entity, combining into single LLM call", flush=True)
                        print(f"Shared context: {significant_common}", flush=True)

                        relevant_context, resolved_question = retrieve_relevant_chunks(
                            combined_question,
                            session,
                            chat_history,
                            document_filter=doc_filter,
                            strategy_hint="semantic",
                            metadata_filters={},
                            question_type="general"
                        )

                        if relevant_context:
                            context_text = format_context_with_metadata(relevant_context)
                            sources = extract_source_documents(relevant_context)

                            # Ask LLM to answer all parts at once with deduplication instruction
                            payload = {
                                "context": context_text,
                                "history": "None",
                                "question": f"{resolved_question}\n\nIMPORTANT: Structure your answer clearly for each part of the question. If the same information applies to multiple parts, mention it only once.",
                            }

                            logging.info("Invoking LLM with combined question...")
                            answer_text = session.rag_chain.invoke(payload)

                            print(f"Combined answer generated: {len(answer_text)} chars", flush=True)
                            print("----- DEBUG: END QUERY PROCESSING -----", flush=True)

                            return {
                                "answer": answer_text,
                                "sources": list(sources)
                            }

            # Standard path: Process each sub-question independently
            sub_answers = []
            all_sources = set()

            for sub_q in sub_questions:
                question_text = sub_q["question"]
                strategy_hint = sub_q.get("strategy", "semantic")
                filters_hint = sub_q.get("filters", {})
                question_type = sub_q.get("type", "general")

                logging.info("Processing sub-question: %s (Strategy: %s)", question_text, strategy_hint)

                # Retrieve context for this specific sub-question
                relevant_context, resolved_question = retrieve_relevant_chunks(
                    question_text,
                    session,
                    chat_history,
                    document_filter=doc_filter,
                    strategy_hint=strategy_hint,
                    metadata_filters=filters_hint,
                    question_type=question_type
                )

                if not relevant_context:
                    sub_answers.append({
                        "question": question_text,
                        "answer": f"Information for '{question_text}' is not available in the provided documents.",
                        "sources": []
                    })
                    continue

                # Extract sources
                sources = extract_source_documents(relevant_context)
                all_sources.update(sources)

                # Format context
                context_text = format_context_with_metadata(relevant_context)

                # Get answer from LLM (history isolated)
                payload = {
                    "context": context_text,
                    "history": "None",  # Isolated - rely only on retrieved context
                    "question": resolved_question,  # Use resolved question for better understanding
                }

                logging.info("Invoking LLM for sub-question...")
                answer_text = session.rag_chain.invoke(payload)

                sub_answers.append({
                    "question": question_text,
                    "answer": answer_text,
                    "sources": sources,
                    "type": question_type
                })

                logging.info("Sub-answer generated: %s chars", len(answer_text))

            # Synthesize all sub-answers into final answer
            final_answer = synthesize_answers(sub_answers, user_input)

            print(f"Synthesized final answer: {len(final_answer)} chars", flush=True)
            print("----- DEBUG: END QUERY PROCESSING -----", flush=True)

            return {
                "answer": final_answer,
                "sources": list(all_sources)
            }

        else:
            # Single question - process normally
            # Use the type/strategy determined by valid analysis
            primary_intent = sub_questions[0]
            strategy_hint = primary_intent.get("strategy", "semantic")
            filters_hint = primary_intent.get("filters", {})
            question_type = primary_intent.get("type", "general")

            relevant_context, resolved_question = retrieve_relevant_chunks(
                user_input,
                session,
                chat_history,
                document_filter=doc_filter,
                strategy_hint=strategy_hint,
                metadata_filters=filters_hint,
                question_type=question_type
            )
            logging.info("Number of context entries retrieved: %d", len(relevant_context))
            logging.info("Resolved question for LLM: %s", resolved_question)

            # Determine retrieval mode used
            strategy = determine_retrieval_strategy(user_input, strategy_hint, filters_hint)
            retrieval_mode = strategy['mode']

            # Extract source documents
            sources = extract_source_documents(relevant_context)

            if retrieval_mode == 'conversational':
                context_text = "No documents needed for this conversational turn."
                history_text = format_chat_history(chat_history)
                payload = {
                    "context": context_text,
                    "history": history_text,
                    "question": resolved_question,
                }
                print("--- DEBUG: CONVERSATIONAL MODE ---", flush=True)
                print("Using chat history for context.", flush=True)
            else:
                context_text = format_context_with_metadata(relevant_context)
                
                # History is only used for query rewriting, not sent to LLM
                # This prevents conversation memory from contaminating answers
                payload = {
                    "context": context_text,
                    "history": "None",  # Isolated - rely only on retrieved context
                    "question": resolved_question,  # Use resolved question instead of original
                }

            print("----- DEBUG: INVOKING LLM -----", flush=True)
            if resolved_question != user_input:
                print(f"Original Q: '{user_input}'", flush=True)
                print(f"Resolved Q: '{resolved_question}'", flush=True)
            answer_text = session.rag_chain.invoke(payload)
            print("----- DEBUG: LLM RAW RESPONSE -----", flush=True)
            print(answer_text, flush=True)
            print("----- DEBUG: END LLM RESPONSE -----", flush=True)

            print(f"Answer generated successfully: {len(answer_text)} chars", flush=True)

            # Use LLM-based validation for better accuracy (with heuristic fallback)
            if retrieval_mode == 'conversational':
                validation_result = {
                    "is_complete": True,
                    "confidence": "high",
                    "warning": None,
                    "reasoning": "Conversational query - no validation needed",
                    "num_chunks": 0,
                    "num_documents": 0
                }
            else:
                validation_result = validate_answer_with_llm(
                    user_input,
                    answer_text,
                    relevant_context,
                    retrieval_mode=retrieval_mode
                )
            logging.info("Answer validation: confidence=%s, complete=%s",
                         validation_result["confidence"], validation_result["is_complete"])

            # Append warning if needed
            final_answer = append_validation_warning(answer_text, validation_result)

            logging.info("----- DEBUG: END QUERY PROCESSING -----")
            return {
                "answer": final_answer,
                "sources": sources
            }

    except Exception as exc:  # pylint: disable=broad-except
        error_msg = str(exc)
        logging.error("Error processing question: %s", error_msg, exc_info=True)

        user_friendly_error = f"Error: {error_msg}"
        if "replace" in error_msg:
            user_friendly_error = "Error: Document formatting issue. Please reprocess your documents."
        if "API" in error_msg or "Gemini" in error_msg or "Google" in error_msg:
            user_friendly_error = "Error: API connection issue. Please check your GEMINI_API_KEY."

        return {
            "answer": user_friendly_error,
            "sources": []
        }


def add_documents_to_existing_session(uploaded_files, session_id: str, session_manager):
    """Add new documents to an existing chat session.

    Args:
        uploaded_files: Files to add (can be UploadFile objects or file paths)
        session_id: ID of the session to update
        session_manager: SessionManager instance

    Returns:
        dict with:
            - success: bool
            - message: str
            - filenames: list of added filenames

    Raises:
        Exception if processing fails
    """
    try:
        # Get session info
        session_info = session_manager.get_session_info(session_id)
        if not session_info:
            raise ValueError(f"Session {session_id} not found")

        collection_name = session_info['collection_name']

        # Save uploaded files temporarily with unique naming
        temp_dir = Path(tempfile.mkdtemp())
        saved_files = []
        original_filenames = []

        try:
            # Handle different upload file formats
            for file in uploaded_files:
                # Check if it's already a file path (from API endpoint)
                if isinstance(file, (str, Path)):
                    file_path = Path(file)
                    if file_path.exists():
                        original_filenames.append(file_path.name)
                        saved_files.append(str(file_path))
                elif hasattr(file, 'name'):
                    # UploadFile object (from FastAPI)
                    filename = file.name
                    original_filenames.append(filename)
                    temp_path = temp_dir / filename

                    if hasattr(file, 'file'):
                        # File-like object
                        with open(temp_path, 'wb') as f:
                            shutil.copyfileobj(file.file, f)
                    elif hasattr(file, 'read'):
                        # BytesIO or similar
                        with open(temp_path, 'wb') as f:
                            f.write(file.read())

                    saved_files.append(str(temp_path))

            if not saved_files:
                raise ValueError("No valid files provided")

            logging.info("Processing %d files for session %s", len(saved_files), session_id)

            # Load and process new documents
            docs = load_docs(saved_files, original_filenames)
            if not docs:
                raise ValueError("No content extracted from uploaded files")

            logging.info("Loaded %d documents from new files", len(docs))

            # Chunk the documents
            splits = get_document_chunks(docs)
            logging.info("Created %d chunks from new documents", len(splits))

            # Add to session using SessionManager
            success = session_manager.add_documents_to_session(
                session_id=session_id,
                new_docs=splits,
                new_original_filenames=original_filenames
            )

            if not success:
                raise Exception("Failed to add documents to session")

            # Format document names nicely for display
            doc_names = ", ".join(original_filenames)
            message = f"Successfully added {len(original_filenames)} document(s): {doc_names}"

            return {
                "success": True,
                "message": message,
                "filenames": original_filenames
            }

        finally:
            # Clean up temp directory
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logging.warning("Could not clean up temp directory: %s", e)

    except Exception as e:
        logging.error("Error adding documents to session %s: %s", session_id, e, exc_info=True)
        raise


__all__ = [
    "format_chat_history",
    "build_rag_chain",
    "retrieve_relevant_chunks",
    "proceed_input",
    "process_user_question",
    "add_documents_to_existing_session",
]
