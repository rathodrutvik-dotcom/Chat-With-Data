"""
Question decomposition module for handling multi-intent queries.

This module breaks down complex questions into simpler sub-questions that can
be processed independently and then synthesized into a comprehensive answer.
"""

import logging
import re
from typing import List, Dict, Optional


def detect_multi_intent_question(question: str) -> bool:
    """
    Detect if a question contains multiple intents or asks about multiple topics.
    
    Args:
        question: The user's question
        
    Returns:
        True if the question has multiple intents, False otherwise
    """
    question_lower = question.lower()
    
    # Check for coordinating conjunctions that often link multiple questions
    multi_intent_patterns = [
        r'\band\s+(what|how|when|where|who|which|give|tell|provide|show)',
        r'\balso\s+(what|how|when|where|who|which|give|tell|provide|show)',
        r'\bplus\s+(what|how|when|where|who|which)',
        r'[?]\s+(what|how|when|where|who|which)',  # Multiple question marks
        r'\band\s+also',
        r',\s*and\s+(what|how|when|where|who|which)',
    ]
    
    for pattern in multi_intent_patterns:
        if re.search(pattern, question_lower):
            return True
    
    # Check for multiple distinct information requests
    info_requests = [
        'what is',
        'how many',
        'when is',
        'where is',
        'who is',
        'give me',
        'tell me',
        'provide',
        'list',
        'show',
        'explain',
        'describe',
    ]
    
    request_count = sum(1 for req in info_requests if req in question_lower)
    if request_count >= 2:
        return True
    
    return False


def decompose_question(question: str) -> List[Dict[str, str]]:
    """
    Decompose a complex multi-intent question into simpler sub-questions.
    
    Args:
        question: The user's complex question
        
    Returns:
        List of dictionaries containing sub-questions with metadata:
        [{"question": "sub-question text", "type": "specific/timeline/count/etc"}]
    """
    if not detect_multi_intent_question(question):
        # Single intent - return as-is
        return [{"question": question, "type": "single", "original": True}]
    
    logging.info("Detected multi-intent question, decomposing: %s", question)
    
    # Split on common conjunctions and punctuation
    sub_questions = []
    
    # Strategy 1: Split on "and [question-word]" patterns
    and_split_pattern = r'\s+and\s+(what|how|when|where|who|which|give|tell|provide|show|list)'
    parts = re.split(and_split_pattern, question, flags=re.IGNORECASE)
    
    if len(parts) > 1:
        # Reconstruct sub-questions
        current_q = parts[0].strip()
        for i in range(1, len(parts), 2):
            if i < len(parts):
                # Add previous question
                if current_q and not current_q.endswith('?'):
                    current_q += '?'
                if current_q:
                    sub_questions.append(current_q)
                
                # Start new question with the question word
                if i + 1 < len(parts):
                    current_q = parts[i] + ' ' + parts[i + 1].strip()
                else:
                    current_q = parts[i].strip()
        
        # Add the last question
        if current_q:
            if not current_q.endswith('?'):
                current_q += '?'
            sub_questions.append(current_q)
    
    # Strategy 2: Split on multiple question marks
    if not sub_questions:
        q_parts = [p.strip() for p in question.split('?') if p.strip()]
        if len(q_parts) > 1:
            sub_questions = [p + '?' for p in q_parts]
    
    # Strategy 3: Split on commas followed by question words
    if not sub_questions:
        comma_pattern = r',\s*(and\s+)?(what|how|when|where|who|which)'
        parts = re.split(comma_pattern, question, flags=re.IGNORECASE)
        if len(parts) > 1:
            base = parts[0].strip()
            for i in range(1, len(parts), 3):  # Skip the 'and' and question word groups
                if i + 1 < len(parts):
                    q = parts[i + 1] + ' ' + (parts[i + 2] if i + 2 < len(parts) else '')
                    if not q.strip().endswith('?'):
                        q = q.strip() + '?'
                    sub_questions.append(q.strip())
            
            # Add the base question
            if base and not base.endswith('?'):
                base += '?'
            sub_questions.insert(0, base)
    
    # If no decomposition worked, return original
    if not sub_questions or len(sub_questions) == 1:
        sub_questions = [question]
    
    # Clean and categorize sub-questions
    processed = []
    for q in sub_questions:
        q = q.strip()
        if not q:
            continue
        
        # Ensure it ends with a question mark
        if not q.endswith('?'):
            q += '?'
        
        # Determine question type for better handling
        q_lower = q.lower()
        q_type = "general"
        
        if any(word in q_lower for word in ["how many", "count", "number of"]):
            q_type = "count"
        elif any(word in q_lower for word in ["timeline", "when", "date", "schedule"]):
            q_type = "timeline"
        elif any(word in q_lower for word in ["where", "location"]):
            q_type = "location"
        elif any(word in q_lower for word in ["list", "all", "what are"]):
            q_type = "list"
        elif any(word in q_lower for word in ["objective", "goal", "purpose"]):
            q_type = "objective"
        elif any(word in q_lower for word in ["scope", "coverage"]):
            q_type = "scope"
        elif any(word in q_lower for word in ["budget", "cost"]):
            q_type = "budget"
        
        processed.append({
            "question": q,
            "type": q_type,
            "original": False
        })
    
    logging.info("Decomposed into %d sub-questions: %s", len(processed), [p["question"] for p in processed])
    
    return processed


def extract_document_filter_from_question(question: str) -> Optional[str]:
    """
    Extract document name if the question explicitly mentions a document.
    
    Args:
        question: The user's question
        
    Returns:
        Document name if mentioned, None otherwise
    """
    question_lower = question.lower()
    
    # Common patterns for document references
    patterns = [
        r'in\s+([a-zA-Z0-9_\-\.]+\.(?:pdf|docx?|xlsx?))',
        r'from\s+([a-zA-Z0-9_\-\.]+\.(?:pdf|docx?|xlsx?))',
        r'(?:document|file)\s+([a-zA-Z0-9_\-\.]+\.(?:pdf|docx?|xlsx?))',
        r'([a-zA-Z0-9_\-\.]+\.(?:pdf|docx?|xlsx?))',  # Just the filename
    ]
    
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            doc_name = match.group(1)
            logging.info("Extracted document filter: %s", doc_name)
            return doc_name
    
    return None


def synthesize_answers(sub_answers: List[Dict[str, str]], original_question: str) -> str:
    """
    Synthesize multiple sub-answers into a coherent response.
    
    Args:
        sub_answers: List of {"question": str, "answer": str, "sources": List[str]}
        original_question: The original complex question
        
    Returns:
        Synthesized answer combining all sub-answers
    """
    if not sub_answers:
        return "No information found for this question."
    
    if len(sub_answers) == 1:
        return sub_answers[0]["answer"]
    
    # Build a structured response
    parts = []
    
    for idx, sub_answer in enumerate(sub_answers, 1):
        answer_text = sub_answer.get("answer", "").strip()
        
        # Skip empty or error answers
        if not answer_text or "not available" in answer_text.lower():
            continue
        
        # For the first answer or if answers are short, just append
        if idx == 1 or len(answer_text) < 100:
            parts.append(answer_text)
        else:
            # For subsequent longer answers, add a subtle separator
            parts.append(answer_text)
    
    if not parts:
        return "The requested information is not available in the provided documents."
    
    # Join with appropriate spacing
    result = " ".join(parts)
    
    return result


__all__ = [
    "detect_multi_intent_question",
    "decompose_question",
    "extract_document_filter_from_question",
    "synthesize_answers",
]
