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
            """Analyze the following user question for a RAG (Retrieval-Augmented Generation) system that processes multiple documents.{doc_context}{history_context}
            
            CRITICAL INSTRUCTIONS:
            
            1. **Question Decomposition**: If the question contains multiple distinct intents, break it down into separate sub-questions.
               When breaking down questions, resolve pronouns ("them", "it", "they") by using the conversation history context:
               - "How many projects? Give me names of them" → ["How many projects?", "Give me names of the projects"]
               - "Who is the lead? What is their role?" → ["Who is the lead?", "What is the role of the lead?"]
               - If conversation history mentions "AI-Powered Document project" and user asks "what about it?", resolve "it" to "AI-Powered Document project"
               - Use the most recent relevant entity from conversation history to replace vague pronouns
            
            2. **Retrieval Strategy Selection** (MOST IMPORTANT):
               
               Understand the user's INTENT, not just keywords. Consider paraphrases and implicit needs.
               
               Use "exhaustive" strategy when the question requires information from MULTIPLE sources:
               - Listing/enumerating: "list all", "what are all", "give me all", "show me all", "name all"
                 * Also: "enumerate", "tell me about each", "describe every", "mention all"
               - Counting/quantifying: "how many", "count", "total number", "number of"
                 * Also: "quantity of", "amount of", "how much"
               - Summarizing across documents: "summarize all", "overview of all", "tell me about all"
                 * Also: "give me summary", "what's the overview"
               - Multiple items: "what projects", "which documents", "all locations", "every person"
                 * Also: "the projects" (when multiple exist), "project costs" (implies all projects)
               - Comparative analysis: "compare", "differences between", "similarities across"
               
               IMPORTANT: If the question COULD involve multiple documents/items, use exhaustive.
               Example: "project budgets" → exhaustive (assumes multiple projects exist)
               Example: "tell me about projects" → exhaustive (multiple projects implied)
               
               EXAMPLES OF EXHAUSTIVE QUERIES:
               - "list out all projects name" → exhaustive
               - "how many projects are there" → exhaustive
               - "what are all the locations mentioned" → exhaustive
               - "give me names of all team members" → exhaustive
               - "summarize all project budgets" → exhaustive
               - "what projects exist" → exhaustive
               - "show all timelines" → exhaustive
               
               Use "semantic" strategy ONLY for:
               - Specific fact retrieval: "what is the budget of Project X"
               - Single entity queries: "who is the lead of Alpha project"
               - Targeted information: "what is the deadline for Project Y"
               - Definition/explanation: "what does term X mean"
               
               EXAMPLES OF SEMANTIC QUERIES:
               - "what is the budget of AI-Powered Document Intelligence Platform" → semantic
               - "who is the project lead for Project Alpha" → semantic
               - "when is the deadline for the first milestone" → semantic
            
            3. **Question Type Classification**:
               - "count": Questions asking for quantities (how many, count, total number)
               - "list": Questions asking for enumeration (list all, what are, give me names)
               - "timeline": Questions about schedules, dates, deadlines
               - "general": Other informational queries
            
            4. **Metadata Filters**:
               Extract filters ONLY for explicit structural attributes like "section: budget" or "type: table".
               Do NOT create metadata filters for content-based terms (project names, people, locations, dates).
               Return empty filters {{}} unless there's an explicit structural constraint.
            
            IMPORTANT: When in doubt between exhaustive and semantic, lean towards exhaustive for any query that 
            might require information from multiple documents or sources.
            
            Output strictly JSON (no markdown formatting):
            {{
                "sub_questions": [
                    {{
                        "question": "text of sub question with pronouns resolved",
                        "type": "count|list|timeline|general",
                        "strategy": "exhaustive|semantic",
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
    for sub_answer in sub_answers:
        answer_text = sub_answer.get("answer", "").strip()
        if not answer_text:
            continue
        
        # Check if answer has useful content
        answer_lower = answer_text.lower()
        is_empty_answer = (
            "not available" in answer_lower or
            "information is not available" in answer_lower
        )
        
        if not is_empty_answer:
            valid_answers.append(sub_answer)
    
    if not valid_answers:
        return "The requested information is not available in the provided documents."
    
    # If only one valid answer, return it
    if len(valid_answers) == 1:
        return valid_answers[0]["answer"]
    
    # Use LLM to intelligently synthesize multiple answers
    try:
        llm = get_llm()
        if not llm:
            raise RuntimeError("LLM is required for answer synthesis. Please configure GEMINI_API_KEY.")
        
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
            1. **Deduplicate Information**: If the same fact appears in multiple answers, mention it ONLY ONCE.
            2. **Clean Structure**: Organize information logically based on what was asked:
               - If asked about multiple attributes (location, budget, timeline), present each clearly
               - Use bullet points or clean formatting for multiple distinct pieces of information
               - Start each distinct piece of info on a new line when appropriate
            3. **Preserve Citations**: Keep all [document.pdf] citations from the original answers
            4. **No Meta-Commentary**: Don't say "According to answer 1" or "Based on the answers"
            5. **Natural Flow**: Write as if answering the original question directly
            6. **Avoid Repetition**: If budget is mentioned twice, include it only once
            
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
        raise RuntimeError(f"Answer synthesis failed: {e}") from e


__all__ = [
    "analyze_query",
    "extract_document_filter_from_question",
    "synthesize_answers",
]
