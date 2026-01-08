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
from models.session import RagSession, PipelineResult
from prompts.system_prompt import read_system_prompt
from retrieval.query_rewrite import generate_query_variations, rewrite_query
from retrieval.question_decomposition import (
    decompose_question,
    detect_multi_intent_question,
    extract_document_filter_from_question,
    synthesize_answers,
)
from retrieval.answer_validation import (
    validate_context_completeness,
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
from vectorstore.chroma_store import get_vector_store, reset_embedding_store, get_all_chunks_by_metadata
from retrieval.answer_validation import is_counting_question


def determine_retrieval_strategy(question: str, question_type: str = None):
    """
    Determine retrieval strategy based on question type.
    
    Returns dict with:
        - mode: 'exhaustive' or 'semantic'
        - k: TopK value for semantic mode
        - metadata_filter: Dict of metadata filters for exhaustive mode
    """
    question_lower = question.lower()
    
    # Check if it's a counting/enumeration question
    is_counting = is_counting_question(question) or question_type in ['count', 'list']
    
    # Check for "list all" or "all projects" patterns
    is_exhaustive = any([
        'list all' in question_lower,
        'all projects' in question_lower,
        'how many projects' in question_lower,
        'enumerate' in question_lower,
        'total projects' in question_lower,
        'what are all' in question_lower,
    ])
    
    if is_counting or is_exhaustive:
        # Use exhaustive retrieval with metadata filtering
        metadata_filter = None
        
        # Determine what entity type to filter for
        if 'project' in question_lower:
            metadata_filter = {"contains_projects": True}
        elif 'person' in question_lower or 'people' in question_lower:
            metadata_filter = {"contains_persons": True}
        elif 'location' in question_lower:
            metadata_filter = {"contains_locations": True}
        elif 'date' in question_lower or 'timeline' in question_lower:
            metadata_filter = {"contains_dates": True}
            
        logging.info("Retrieval strategy: EXHAUSTIVE (metadata_filter=%s)", metadata_filter)
        return {
            'mode': 'exhaustive',
            'k': None,  # No TopK limit
            'metadata_filter': metadata_filter
        }
    else:
        # Use semantic TopK retrieval
        # Adaptive k based on question specificity
        if any(word in question_lower for word in ['what is', 'define', 'explain']):
            k = 20  # Specific fact queries - smaller k
        else:
            k = 50  # Default semantic search
            
        logging.info("Retrieval strategy: SEMANTIC (k=%d)", k)
        return {
            'mode': 'semantic',
            'k': k,
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


def retrieve_relevant_chunks(user_input, session: RagSession, chat_history=None, document_filter=None, question_type=None):
    """
    Retrieves the most relevant chunks based on query type and adaptive strategy.
    
    Uses:
    1. Adaptive retrieval strategy (exhaustive vs semantic)
    2. Query rewriting to generate variations
    3. Dense (semantic) retrieval from vector store
    4. Sparse (BM25-style) retrieval from TF-IDF index
    5. Score merging and reranking
    6. Deduplication and diversity assembly
    
    Args:
        user_input: Original user question
        session: RagSession with vectorstore and sparse index
        chat_history: Chat history for context-aware rewriting
        document_filter: Optional document name to filter results
        question_type: Type of question from decomposition (count, list, etc.)
        
    Returns:
        List of context entries with documents, scores, and metadata
    """
    # Step 0: Determine retrieval strategy
    strategy = determine_retrieval_strategy(user_input, question_type)
    
    if strategy['mode'] == 'exhaustive':
        # EXHAUSTIVE MODE: Retrieve all matching chunks without TopK limit
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
        context_entries = assemble_context_entries(unique_entries, max_chunks=100, exhaustive_mode=True)
        
        logging.info("Exhaustive mode - Final context entries: %d", len(context_entries))
        if len(context_entries) == 0:
            logging.warning("⚠️ Exhaustive retrieval returned 0 results! Check metadata and filters.")
        return context_entries
    
    else:
        # SEMANTIC MODE: Use TopK with query variations
        logging.info("Using SEMANTIC retrieval mode with k=%d", strategy['k'])
        retrieval_k = strategy['k']  # Use adaptive k value
        
        rewritten_query = rewrite_query(user_input, chat_history)
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
    
    # Assemble context with document diversity
    context_entries = assemble_context_entries(unique_entries)
    logging.info("Final context entries selected: %d", len(context_entries))
    
    # Log document distribution
    doc_distribution = {}
    for entry in context_entries:
        doc_name = entry["doc"].metadata.get("document_name", "unknown")
        doc_distribution[doc_name] = doc_distribution.get(doc_name, 0) + 1
    logging.info("Document distribution in context: %s", doc_distribution)
    
    return context_entries


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

        logging.info("User Q: %s", user_input)
        
        # Check for explicit document filter in the question
        doc_filter = extract_document_filter_from_question(user_input)
        if doc_filter:
            logging.info("Detected document filter: %s", doc_filter)
        
        # Decompose question if it has multiple intents
        sub_questions = decompose_question(user_input)
        
        if len(sub_questions) > 1:
            logging.info("Processing %d sub-questions separately", len(sub_questions))
            
            # Process each sub-question independently
            sub_answers = []
            all_sources = set()
            
            for sub_q in sub_questions:
                question_text = sub_q["question"]
                question_type = sub_q["type"]
                
                logging.info("Processing sub-question (%s): %s", question_type, question_text)
                
                # Retrieve context for this specific sub-question
                relevant_context = retrieve_relevant_chunks(
                    question_text, 
                    session, 
                    chat_history,
                    document_filter=doc_filter,
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
                    "question": question_text,
                }
                
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
            
            logging.info("Synthesized final answer: %s chars", len(final_answer))
            
            return {
                "answer": final_answer,
                "sources": list(all_sources)
            }
        
        else:
            # Single question - process normally
            relevant_context = retrieve_relevant_chunks(
                user_input, 
                session, 
                chat_history,
                document_filter=doc_filter
            )
            logging.info("Number of context entries retrieved: %d", len(relevant_context))
            
            # Determine retrieval mode used (check if it was exhaustive)
            strategy = determine_retrieval_strategy(user_input, None)
            retrieval_mode = strategy['mode']
            
            # Extract source documents
            sources = extract_source_documents(relevant_context)
            
            context_text = format_context_with_metadata(relevant_context)
            
            # Debug: Log the context being sent to LLM
            logging.info("=" * 80)
            logging.info("CONTEXT BEING SENT TO LLM:")
            logging.info(context_text)
            logging.info("=" * 80)
            
            # History is only used for query rewriting, not sent to LLM
            # This prevents conversation memory from contaminating answers
            payload = {
                "context": context_text,
                "history": "None",  # Isolated - rely only on retrieved context
                "question": user_input,
            }
            answer_text = session.rag_chain.invoke(payload)
            logging.info("Answer generated successfully: %s chars", len(answer_text))
            
            # Validate answer completeness with retrieval mode context
            validation_result = validate_context_completeness(
                user_input, 
                relevant_context, 
                answer_text,
                retrieval_mode=retrieval_mode
            )
            logging.info("Answer validation: confidence=%s, complete=%s", 
                        validation_result["confidence"], validation_result["is_complete"])
            
            # Append warning if needed
            final_answer = append_validation_warning(answer_text, validation_result)
            
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
        if "API" in error_msg or "Groq" in error_msg:
            user_friendly_error = "Error: API connection issue. Please check your GROQ_API_KEY."
        if "Gemini" in error_msg or "Google" in error_msg:
            user_friendly_error = "Error: API connection issue. Please check your GEMINI_API_KEY."
            
        return {
            "answer": user_friendly_error,
            "sources": []
        }


__all__ = [
    "format_chat_history",
    "build_rag_chain",
    "retrieve_relevant_chunks",
    "proceed_input",
    "process_user_question",
]
