"""
Answer validation and context completeness checking.

This module provides guardrails to detect when retrieved context might be incomplete
and warns users appropriately to avoid overconfident wrong answers.
"""

import logging
from typing import List, Dict
from config.settings import GEMINI_MODEL
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser


def get_llm():
    """Helper to get the configured LLM for validation."""
    return ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0.0)


def validate_answer_with_llm(
    question: str,
    answer: str,
    context_entries: List[Dict],
    retrieval_mode: str = "semantic"
) -> Dict:
    """
    Use LLM to dynamically validate answer quality and completeness.

    This replaces static heuristics with intelligent analysis that:
    - Understands paraphrased questions
    - Detects semantic incompleteness
    - Adapts to different document types
    - Provides reasoning for debugging

    Args:
        question: User's original question
        answer: Generated answer text
        context_entries: Retrieved context chunks
        retrieval_mode: 'semantic' or 'exhaustive'

    Returns:
        Dictionary with validation results and suggested warnings
    """
    try:
        llm = get_llm()

        # Extract document information
        documents_seen = set()
        for entry in context_entries:
            doc = entry.get("doc")
            if doc and doc.metadata:
                doc_name = doc.metadata.get("document_name")
                if doc_name:
                    documents_seen.add(doc_name)

        num_documents = len(documents_seen)
        num_chunks = len(context_entries)
        doc_list = list(documents_seen) if documents_seen else ["unknown"]

        # Get a sample of context to help LLM understand what was retrieved
        context_sample = ""
        if context_entries:
            sample_chunks = context_entries[:3]  # First 3 chunks
            context_sample = "\n".join([
                f"- {entry['doc'].page_content[:150]}..."
                for entry in sample_chunks if entry.get('doc')
            ])

        prompt = ChatPromptTemplate.from_template(
            """You are an answer quality validator for a RAG (Retrieval-Augmented Generation) system.

Task: Evaluate if the generated answer adequately addresses the user's question given the available context.

User Question: {question}

Generated Answer: {answer}

Context Information:
- Retrieved Chunks: {num_chunks}
- Source Documents: {num_documents} ({doc_list})
- Retrieval Mode: {retrieval_mode}

Sample Context (first 3 chunks):
{context_sample}

Analyze:
1. Does the answer directly address what the user asked?
2. For list/count/enumeration queries: Are all items included or is the count complete?
3. For multi-document queries: Is coverage comprehensive across relevant documents?
4. Are there indicators of uncertainty or missing information in the answer?
5. Does the retrieved context seem sufficient for a complete answer?
6. Are there obvious gaps or limitations?

Consider:
- Paraphrased requests (e.g., "enumerate all" = "list all" = "give me every")
- Implicit multi-document needs (e.g., "project costs" when multiple projects exist)
- Context limitations vs answer limitations

Output JSON (no markdown):
{{
    "is_complete": true/false,
    "confidence": "high|medium|low",
    "reasoning": "2-3 sentence explanation of assessment",
    "missing_aspects": ["aspect1", "aspect2"] or [],
    "suggested_warning": "user-facing warning message" or null,
    "num_chunks": {num_chunks},
    "num_documents": {num_documents}
}}"""
        )

        chain = prompt | llm | JsonOutputParser()
        result = chain.invoke({
            "question": question,
            "answer": answer,
            "num_chunks": num_chunks,
            "num_documents": num_documents,
            "doc_list": ", ".join(doc_list[:5]),  # Limit to 5 doc names
            "retrieval_mode": retrieval_mode,
            "context_sample": context_sample or "No context retrieved"
        })

        # Ensure backward compatibility with expected fields
        validation_result = {
            "is_complete": result.get("is_complete", True),
            "confidence": result.get("confidence", "medium"),
            "warning": result.get("suggested_warning"),
            "reasoning": result.get("reasoning", ""),
            "missing_aspects": result.get("missing_aspects", []),
            "num_chunks": num_chunks,
            "num_documents": num_documents
        }

        logging.info("LLM validation: is_complete=%s, confidence=%s, reasoning=%s",
                     validation_result["is_complete"],
                     validation_result["confidence"],
                     validation_result["reasoning"][:100])

        return validation_result

    except Exception as e:
        logging.error(f"LLM answer validation failed: {e}")
        raise RuntimeError(f"Answer validation failed: {e}") from e


def append_validation_warning(answer: str, validation_result: Dict) -> str:
    """
    Append validation warning to answer if needed.

    Args:
        answer: Original answer text
        validation_result: Result from validate_answer_with_llm

    Returns:
        Answer with optional warning appended
    """
    warning = validation_result.get("warning")

    if warning:
        # Add a line break before the warning
        return f"{answer}\n\n{warning}"

    return answer


__all__ = [
    "validate_answer_with_llm",
    "append_validation_warning",
]
