"""
Question decomposition module for handling multi-intent queries.

This module breaks down complex questions into simpler sub-questions that can
be processed independently and then synthesized into a comprehensive answer.
"""

import logging
import re
from typing import List, Dict, Optional, Any

from config.settings import GEMINI_MODEL
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser


def get_llm():
    """Helper to get the configured LLM."""
    return ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0.0)


def analyze_query(question: str, available_documents: List[str] = None, chat_history: List[Dict] = None) -> List[Dict[str, Any]]:
    """
    Analyze a user query using pure LLM intelligence (no static keywords).
    
    Dynamically determines:
    1. Multi-intent decomposition
    2. Retrieval strategy (exhaustive vs semantic)
    3. Question type and expected response format
    4. Target documents (if applicable)
    
    Args:
        question: User's question
        available_documents: List of available document names for context-aware analysis
        chat_history: Recent conversation history for resolving pronouns and context
    
    Returns:
        List of sub-question dictionaries with strategy, type, and metadata
    """
    logging.info("Analyzing query with LLM: %s", question)
    
    try:
        llm = get_llm()
        if not llm:
            logging.warning("No LLM available for query analysis")
            return [{"question": question, "type": "general", "strategy": "semantic", "filters": {}}]
        
        # Build document context for LLM awareness
        doc_context = ""
        if available_documents:
            doc_list = "\n".join(f"- {doc}" for doc in available_documents[:10])  # Limit to 10
            doc_context = f"\n\nAvailable Documents:\n{doc_list}"

        # Build chat history context for pronoun resolution
        history_context = ""
        if chat_history:
            recent_history = chat_history[-4:] if len(chat_history) >= 4 else chat_history
            history_lines = []
            for msg in recent_history:
                role = "User" if msg.get("role") == "user" else "Assistant"
                content = str(msg.get("content", ""))[:300]  # Limit to 300 chars per message
                history_lines.append(f"{role}: {content}")
            if history_lines:
                history_context = f"\n\nRecent Conversation History:\n" + "\n".join(history_lines)

        prompt = ChatPromptTemplate.from_template(
            """You are an intent analyzer for a multi-document RAG system.{doc_context}{history_context}

TASKS:

1. Question Decomposition  
- If the user question has multiple intents, split it into independent sub-questions.  
- Resolve pronouns (it, they, them, this) using the most recent relevant entity from conversation history.

2. Retrieval Strategy Selection (CRITICAL)  
Choose ONE strategy per sub-question based on intent:

- conversational  
  Use for greetings, acknowledgments, gratitude, self-introduction, or questions about the AI/user NOT related to documents.

- exhaustive  
  Use when the query implies MULTIPLE documents or entities, including:
  • listing, counting, summarizing, comparing  
  • plural or collective references (projects, documents, timelines, budgets)  
  • cases where multiple sources may be needed

- semantic  
  Use ONLY for specific, single-entity or single-fact queries.

Rule: If unsure between exhaustive and semantic, choose exhaustive.

3. Question Type Classification  
Assign one type:
- count: quantities or totals  
- list: enumeration  
- timeline: dates, schedules, deadlines  
- general: other factual queries  
- chat: conversational input

4. Metadata Filters  
Extract filters ONLY if the user explicitly specifies structural constraints (e.g., section, format, type).  
Do NOT infer filters from content. Default to {{}}.

OUTPUT FORMAT (strict JSON, no markdown):
{{
  "sub_questions": [
    {{
      "question": "resolved sub-question text",
      "type": "count|list|timeline|general|chat",
      "strategy": "exhaustive|semantic|conversational",
      "filters": {{}}
    }}
  ]
}}

User Question: {question}
"""
        )
        
        chain = prompt | llm | JsonOutputParser()
        result = chain.invoke({
            "question": question,
            "doc_context": doc_context,
            "history_context": history_context
        })
        
        sub_questions = result.get("sub_questions", [])
        
        if not sub_questions:
            logging.warning("LLM returned empty sub_questions for: %s", question)
            return [{"question": question, "type": "general", "strategy": "semantic", "filters": {}}]
        
        logging.info("LLM Analysis Result: %s", sub_questions)
        return sub_questions

    except Exception as e:
        logging.error(f"LLM query analysis failed: {e}")
        return [{"question": question, "type": "general", "strategy": "semantic", "filters": {}}]


def extract_document_filter_from_question(question: str) -> Optional[str]:
    """
    Extract document name if the question explicitly mentions a document.
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
    Uses LLM to intelligently combine answers, removing redundancy and improving structure.
    """
    if not sub_answers:
        return "No information found for this question."
    
    if len(sub_answers) == 1:
        return sub_answers[0]["answer"]
    
    # Filter out empty/unavailable answers
    valid_answers = []
    
    # improved negative detection patterns
    negative_patterns = [
        "not available",
        "no information found",
        "could not find",
        "cannot find",
        "does not mention",
        "unable to find",
        "no mention of",
        "information is not available",
        "no relevant information",
        "i cannot confirm"
    ]
    
    for sub_answer in sub_answers:
        answer_text = sub_answer.get("answer", "").strip()
        if not answer_text:
            continue
        
        # Check if answer has useful content
        answer_lower = answer_text.lower()
        is_empty_answer = any(pattern in answer_lower for pattern in negative_patterns)
        
        # Special case: if the answer is very short and contains negative words, it's likely empty
        if len(answer_text) < 100 and is_empty_answer:
             pass # It is empty
        # If it's long, it might be "I could not find X, but found Y..." - so we keep it if it's long? 
        # Actually, safer to trust the patterns for "I could not find" at the start.
        elif answer_lower.startswith("i could not find") or answer_lower.startswith("i cannot find"):
             is_empty_answer = True
        else:
             is_empty_answer = False # Keep it if we are not sure
             
        # Override: if we detected 'not available' in the simple check above, trust it
        if any(pattern in answer_lower for pattern in ["not available in the provided documents", "information is not available"]):
            is_empty_answer = True

        if not is_empty_answer:
            valid_answers.append(sub_answer)
    
    if not valid_answers:
        # If all were filtered out, check if we have any original answers. 
        # If so, return the first one (fallback) instead of a generic message, 
        # unless it was truly empty.
        if sub_answers and sub_answers[0].get("answer"):
             return sub_answers[0]["answer"]
        return "The requested information is not available in the provided documents."
    
    # If only one valid answer, return it
    if len(valid_answers) == 1:
        return valid_answers[0]["answer"]
    
    # Use LLM to intelligently synthesize multiple answers
    try:
        llm = get_llm()
        if not llm:
            return valid_answers[0]["answer"]
        
        # Build context for synthesis
        answers_text = ""
        for idx, sa in enumerate(valid_answers, 1):
            answers_text += f"Sub-answer {idx}: {sa['answer']}\n\n"
        
        synthesis_prompt = ChatPromptTemplate.from_template(
            """You are synthesizing multiple answers into a single, coherent response.
            
            Original Question: {question}
            
            Multiple Answers:
            {answers}
            
            CRITICAL INSTRUCTIONS:
            1. **Prioritize Information**: If one answer has information and another says "not found", ONLY use the one with information.
            2. **Ignore Negatives**: Completely ignore statements like "I could not find..." if other answers provide the facts.
            3. **Deduplicate**: Mention each fact only once.
            4. **Clean Structure**: 
               - Combine lists if multiple answers list items.
               - Used bullet points for distinct items.
            5. **Preserve Citations**: Keep [document.pdf] citations.
            6. **No Meta-Commentary**: Don't mention "Sub-answer 1" or "retrieval".
            7. **Consistency**: Ensure the final answer doesn't contradict itself.
            
            Synthesized Answer:"""
        )
        
        chain = synthesis_prompt | llm | StrOutputParser()
        result = chain.invoke({
            "question": original_question,
            "answers": answers_text
        })
        
        return result.strip()
        
    except Exception as e:
        logging.error(f"Error in LLM-based synthesis: {e}")
        # Fallback to concatenating with newlines
        return "\n\n".join([a["answer"] for a in valid_answers])


__all__ = [
    "analyze_query",
    "extract_document_filter_from_question",
    "synthesize_answers",
]
