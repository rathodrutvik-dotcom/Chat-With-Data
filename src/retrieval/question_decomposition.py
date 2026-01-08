"""
Question decomposition module for handling multi-intent queries.

This module breaks down complex questions into simpler sub-questions that can
be processed independently and then synthesized into a comprehensive answer.
"""

import logging
import re
from typing import List, Dict, Optional


from config.settings import USE_GROQ, USE_GEMINI, GROQ_MODEL, GEMINI_MODEL
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

def get_llm():
    """Helper to get the configured LLM."""
    if USE_GEMINI:
        return ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0.0)
    elif USE_GROQ:
        return ChatGroq(model=GROQ_MODEL, temperature=0.0)
    return None
    """Helper to get the configured LLM."""
    if USE_GEMINI:
        return ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0.0)
    elif USE_GROQ:
        return ChatGroq(model=GROQ_MODEL, temperature=0.0)
    return None

def detect_multi_intent_question(question: str) -> bool:
    """
    Detect if a question contains multiple intents using LLM analysis.
    For performance, we still do a quick regex check first for obvious cases.
    """
    # Fast path: simple questions probably don't need LLM
    if len(question.split()) < 5 and "and" not in question.lower():
        return False

    try:
        llm = get_llm()
        if not llm:
            return False 
            
        prompt = ChatPromptTemplate.from_template(
            """Analyze if the following question asks for multiple distinct pieces of information that would require separate searches.
            Return ONLY textual JSON: {{"is_multi_intent": true/false}}
            
            Question: {question}
            """
        )
        chain = prompt | llm | JsonOutputParser()
        result = chain.invoke({"question": question})
        return result.get("is_multi_intent", False)
    except Exception as e:
        logging.warning(f"LLM intent detection failed: {e}. Falling back to heuristic.")
        # Fallback to simple heuristic
        return " and " in question.lower() or "?" in question.replace(question[-1], "")

def decompose_question(question: str) -> List[Dict[str, str]]:
    """
    Decompose a complex multi-intent question into simpler sub-questions using LLM.
    """
    # Fast check
    if not detect_multi_intent_question(question):
         return [{"question": question, "type": "single", "original": True}]

    logging.info("Decomposing complex question with LLM: %s", question)
    
    try:
        llm = get_llm()
        if not llm:
             raise ValueError("No LLM configured")

        prompt = ChatPromptTemplate.from_template(
            """Break down the following complex user question into a list of atomic, self-contained sub-questions.
            Each sub-question should be standalone and contain all necessary context.
            Identify the type of each question (count, timeline, location, listing, general).
            
            Output strictly JSON format:
            {{
                "sub_questions": [
                    {{"question": "first sub-question?", "type": "topic_type"}},
                    {{"question": "second sub-question?", "type": "topic_type"}}
                ]
            }}
            
            Original Question: {question}
            """
        )
        
        chain = prompt | llm | JsonOutputParser()
        result = chain.invoke({"question": question})
        
        sub_questions = []
        for item in result.get("sub_questions", []):
            sub_questions.append({
                "question": item.get("question"),
                "type": item.get("type", "general"),
                "original": False
            })
            
        if not sub_questions:
            # Fallback if parsing returned empty
            return [{"question": question, "type": "single", "original": True}]
            
        logging.info("LLM decomposed into: %s", sub_questions)
        return sub_questions

    except Exception as e:
        logging.error(f"LLM decomposition failed: {e}. Returning original.")
        return [{"question": question, "type": "single", "original": True}]


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
