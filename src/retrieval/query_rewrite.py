import logging
import re

from config.settings import CHAT_SNIPPET_MAX_CHARS, MAX_MULTI_QUERIES


def get_last_message_by_role(chat_history, role):
    if not chat_history:
        return None
    for message in reversed(chat_history):
        if isinstance(message, dict) and message.get("role") == role:
            return message
    return None


def clean_chat_snippet(text, limit=CHAT_SNIPPET_MAX_CHARS):
    if not text:
        return ""
    if isinstance(text, dict):
        text = text.get("content") or text.get("text") or str(text)
    elif isinstance(text, list):
        text = " ".join(str(item) for item in text)
    else:
        text = str(text)

    snippet = " ".join(text.split())
    return snippet[:limit]



from config.settings import USE_GROQ, USE_GEMINI, GROQ_MODEL, GEMINI_MODEL
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

def rewrite_query(user_input, chat_history):
    """
    Rewrites the user's query to be self-contained by resolving pronouns 
    and references using the chat history.
    """
    trimmed = (user_input or "").strip()
    if not trimmed:
        return trimmed

    # If no history, no need to rewrite
    if not chat_history:
        return trimmed

    # Relaxed condition: If history exists, we should probably check with LLM, 
    # unless it's a very clear standalone query.
    # But for "smart" behavior, we bias towards using LLM if there's any ambiguity.
    
    logging.info("Rewriting query using LLM for better context resolution...")
    
    try:
        # Initialize LLM for rewriting (lightweight)
        llm = None
        if USE_GEMINI:
             llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0.1)
        elif USE_GROQ:
             llm = ChatGroq(model=GROQ_MODEL, temperature=0.1)
        
        if not llm:
            logging.warning("No LLM available for query rewriting, falling back to original.")
            return trimmed

        # Format history string
        history_str = ""
        # Get more history context - need enough to capture enumerated lists from earlier
        # For ordinal references (first/second/third), we need to see the original list
        recent_history = chat_history[-10:] if len(chat_history) >= 10 else chat_history
        
        for msg in recent_history:
            role = "User" if msg.get("role") == "user" else "Assistant"
            # Increase limit to capture full enumerated lists (e.g., list of 4 projects)
            content = clean_chat_snippet(msg.get("content", ""), limit=1000)
            history_str += f"{role}: {content}\n"
        
        logging.info(f"Query rewrite with {len(recent_history)} messages in history")

        prompt = ChatPromptTemplate.from_template(
            """Given the conversation history, rewrite the latest user question to be a standalone search query.
            
            Rules:
            1. If the question is a follow-up (e.g. "what about usage?", "and the cost?"), incorporate context from previous turns.
            2. If the user is answering a clarification question from the AI (Task Refinement), combine the user's new answer with the ORIGINAL user request to form a complete instruction.
               Example:
               - History: User: "Write an email." -> AI: "To whom?" -> User: "My boss."
               - Good Rewrite: "Write an email to my boss." (Preserves "Write an email" intent)
               - Bad Rewrite: "Who is my boss?" (Loses intent)
            3. If the question is already standalone, return it mostly as-is.
            
            Chat History:
            {history}
            
            Latest User Question: {question}
            
            Standalone Query:"""
        )
        
        chain = prompt | llm | StrOutputParser()
        rewritten = chain.invoke({"history": history_str, "question": trimmed})
        
        # Cleanup
        rewritten = rewritten.strip().replace('"', '')
        logging.info(f"Original: '{trimmed}' -> Rewritten: '{rewritten}'")
        return rewritten

    except Exception as e:
        logging.error(f"Error re-writing query: {e}")
        
        # Try fallback with simpler/faster LLM model instead of static concatenation
        try:
            logging.info("Attempting fallback LLM for query rewriting...")
            # Use Groq's faster model as fallback (or Gemini Flash)
            fallback_llm = None
            if USE_GROQ:
                # Mixtral is faster than main model
                fallback_llm = ChatGroq(model="mixtral-8x7b-32768", temperature=0.1)
            elif USE_GEMINI:
                # Gemini Flash is faster
                fallback_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.1)
            
            if fallback_llm and 'history_str' in locals():
                simple_prompt = f"Rewrite as standalone query using this context: {history_str[-200:]}\n\nQuestion: {trimmed}"
                rewritten = fallback_llm.invoke(simple_prompt)
                if isinstance(rewritten, str):
                    return rewritten.strip()
                return str(rewritten).strip()
        except Exception as fallback_error:
            logging.warning(f"Fallback LLM also failed: {fallback_error}")
        
        # Final fallback: return original question
        return trimmed


from langchain_core.output_parsers import JsonOutputParser

def generate_query_variations(rewritten_query, chat_history):
    """Generate query variations using LLM to improve retrieval."""
    if not rewritten_query:
        return []

    logging.info("Generating query variations with LLM...")
    try:
        llm = None
        if USE_GEMINI:
             llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0.3)
        elif USE_GROQ:
             llm = ChatGroq(model=GROQ_MODEL, temperature=0.3)
        
        if not llm:
            return [rewritten_query]

        prompt = ChatPromptTemplate.from_template(
            """Generate 3-5 diverse search query variations for the user question to maximize retrieval coverage.
            Address different aspects: exact keywords, semantic meaning, and related concepts.
            
            User Question: {question}
            
            Output strictly JSON:
            {{ "variations": ["variation 1", "variation 2", "variation 3"] }}
            """
        )
        
        chain = prompt | llm | JsonOutputParser()
        result = chain.invoke({"question": rewritten_query})
        variations = result.get("variations", [])
        
        # Ensure original is included
        if rewritten_query not in variations:
            variations.insert(0, rewritten_query)
            
        logging.info("Generated %d variations via LLM", len(variations))
        return variations[:MAX_MULTI_QUERIES]

    except Exception as e:
        logging.warning(f"LLM variation generation failed: {e}. Falling back to heuristic.")
        
        # --- Fallback to original static logic ---
        variations = [rewritten_query]
        query_lower = rewritten_query.lower()
        if any(word in query_lower for word in ["how many", "list", "all", "count", "what are"]):
            variations.append(f"{rewritten_query} complete list comprehensive")
        if any(word in query_lower for word in ["where", "location", "place"]):
            variations.append(f"{rewritten_query} location address")
            
        return variations


__all__ = [
    "get_last_message_by_role",
    "clean_chat_snippet",
    "rewrite_query",
    "generate_query_variations",
]
