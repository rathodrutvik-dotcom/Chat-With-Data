"""
Answer validation and context completeness checking.

This module provides guardrails to detect when retrieved context might be incomplete
and warns users appropriately to avoid overconfident wrong answers.
"""

import logging
import re
from typing import List, Dict


def is_counting_question(question: str) -> bool:
    """
    Detect if a question asks for counting or listing.
    
    Args:
        question: User's question
        
    Returns:
        True if question asks to count or list items
    """
    question_lower = question.lower()
    
    counting_patterns = [
        r'\bhow many\b',
        r'\bcount\b',
        r'\bnumber of\b',
        r'\bhow much\b',
        r'\blist all\b',
        r'\ball\b.*\b(projects|items|documents|names|dates|locations)\b',
        r'\bwhat are all\b',
        r'\benumerate\b',
        r'\btotal\b.*\b(projects|items|documents)\b',
    ]
    
    for pattern in counting_patterns:
        if re.search(pattern, question_lower):
            return True
    
    return False


def validate_context_completeness(question: str, context_entries: List[Dict], answer: str) -> Dict:
    """
    Validate if the retrieved context is likely complete for the question.
    
    For counting/listing questions, checks if the context entries represent
    comprehensive coverage or if information might be missing.
    
    Args:
        question: User's question
        context_entries: Retrieved context entries
        answer: Generated answer from LLM
        
    Returns:
        Dictionary with:
        - is_complete: bool indicating if context seems complete
        - warning: Optional warning message to append
        - confidence: "high", "medium", or "low"
    """
    if not is_counting_question(question):
        # For non-counting questions, assume context is adequate
        return {
            "is_complete": True,
            "warning": None,
            "confidence": "high"
        }
    
    # For counting questions, analyze context coverage
    if not context_entries:
        return {
            "is_complete": False,
            "warning": "⚠️ No relevant context was found. This answer may be incomplete.",
            "confidence": "low"
        }
    
    # Check document distribution
    documents_seen = set()
    for entry in context_entries:
        doc = entry.get("doc")
        if doc and doc.metadata:
            doc_name = doc.metadata.get("document_name")
            if doc_name:
                documents_seen.add(doc_name)
    
    num_documents = len(documents_seen)
    num_chunks = len(context_entries)
    
    logging.info("Context validation: %d chunks from %d documents", num_chunks, num_documents)
    
    # Heuristics for completeness
    confidence = "high"
    warning = None
    is_complete = True
    
    # Check 1: Very few chunks might mean incomplete retrieval
    if num_chunks < 5:
        confidence = "medium"
        warning = "Note: Retrieved context is limited. If you expected more results, try rephrasing your question."
        is_complete = False
    
    # Check 2: Answer indicates uncertainty
    answer_lower = answer.lower()
    uncertainty_indicators = [
        "may not be complete",
        "might be",
        "appears to be",
        "seems to be",
        "not sure",
        "unclear",
        "may be missing",
    ]
    
    if any(indicator in answer_lower for indicator in uncertainty_indicators):
        confidence = "medium"
        if not warning:
            warning = "Note: The answer indicates some uncertainty. Consider refining your question."
    
    # Check 3: For multi-document queries, ensure we got context from multiple docs
    question_lower = question.lower()
    mentions_multiple = any(word in question_lower for word in ["both", "all", "multiple", "each", "every"])
    
    if mentions_multiple and num_documents < 2:
        confidence = "low"
        warning = "⚠️ Question asks about multiple documents, but context was retrieved from only one. Answer may be incomplete."
        is_complete = False
    
    # Check 4: Check if answer says "not available" but we have context
    if "not available" in answer_lower and num_chunks > 0:
        # This might be a false negative - context was found but didn't contain the answer
        confidence = "medium"
    
    return {
        "is_complete": is_complete,
        "warning": warning,
        "confidence": confidence,
        "num_chunks": num_chunks,
        "num_documents": num_documents
    }


def append_validation_warning(answer: str, validation_result: Dict) -> str:
    """
    Append validation warning to answer if needed.
    
    Args:
        answer: Original answer text
        validation_result: Result from validate_context_completeness
        
    Returns:
        Answer with optional warning appended
    """
    warning = validation_result.get("warning")
    
    if warning:
        # Add a line break before the warning
        return f"{answer}\n\n{warning}"
    
    return answer


__all__ = [
    "is_counting_question",
    "validate_context_completeness",
    "append_validation_warning",
]
