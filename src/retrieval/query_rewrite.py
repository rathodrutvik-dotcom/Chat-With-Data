import logging
import re

from config.settings import CHAT_SNIPPET_MAX_CHARS, FOLLOW_UP_PRONOUNS, MAX_MULTI_QUERIES


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


def rewrite_query(user_input, chat_history):
    trimmed = (user_input or "").strip()
    if not trimmed:
        return trimmed

    words = re.findall(r"\b[\w']+\b", trimmed.lower())
    contains_pronoun = any(word in FOLLOW_UP_PRONOUNS for word in words)
    last_user_message = get_last_message_by_role(chat_history, "user")
    last_assistant_message = get_last_message_by_role(chat_history, "assistant")

    snippets = []
    if contains_pronoun and last_user_message:
        snippet = clean_chat_snippet(last_user_message.get("content", ""))
        if snippet:
            snippets.append(f"Refer to previous user question: {snippet}")
    elif len(words) <= 3 and last_assistant_message:
        snippet = clean_chat_snippet(last_assistant_message.get("content", ""))
        if snippet:
            snippets.append(f"Context from assistant reply: {snippet}")

    rewritten = f"{trimmed} ({' | '.join(snippets)})" if snippets else trimmed
    logging.info("Rewritten query: %s", rewritten)
    return rewritten


def generate_query_variations(rewritten_query, chat_history):
    """Generate query variations to improve multi-document retrieval.
    
    Creates semantic variations that help retrieve information spread across documents.
    """
    if not rewritten_query:
        return []

    variations = [rewritten_query]
    
    # Add semantic variations for better multi-document coverage
    # Extract key terms and concepts for expansion
    query_lower = rewritten_query.lower()
    
    # Handle counting/listing queries
    if any(word in query_lower for word in ["how many", "list", "all", "count", "what are"]):
        variations.append(f"{rewritten_query} complete list comprehensive")
        variations.append(f"enumerate all {rewritten_query}")
    
    # Handle timeline/date queries
    if any(word in query_lower for word in ["timeline", "when", "date", "schedule", "deadline"]):
        variations.append(f"{rewritten_query} schedule dates deadlines milestones")
        variations.append(f"timeline and dates for {rewritten_query}")
    
    # Handle location queries
    if any(word in query_lower for word in ["where", "location", "place", "site"]):
        variations.append(f"{rewritten_query} location address site place")
    
    # Handle project/entity details queries
    if any(word in query_lower for word in ["project", "details", "information", "about"]):
        variations.append(f"comprehensive information {rewritten_query}")
        variations.append(f"all details regarding {rewritten_query}")
    
    # Add context from chat history
    last_assistant_message = get_last_message_by_role(chat_history, "assistant")
    last_user_message = get_last_message_by_role(chat_history, "user")

    if last_assistant_message:
        snippet = clean_chat_snippet(last_assistant_message.get("content", ""))
        if snippet:
            variations.append(f"{rewritten_query} {snippet}")

    if last_user_message:
        snippet = clean_chat_snippet(last_user_message.get("content", ""))
        if snippet:
            variations.append(f"{rewritten_query} Refer to: {snippet}")

    # Keep unique variations
    unique_variations = []
    for variation in variations:
        if variation and variation not in unique_variations:
            unique_variations.append(variation)
        if len(unique_variations) >= MAX_MULTI_QUERIES:
            break
    
    logging.info("Generated %d query variations for comprehensive retrieval", len(unique_variations))
    return unique_variations


__all__ = [
    "get_last_message_by_role",
    "clean_chat_snippet",
    "rewrite_query",
    "generate_query_variations",
]
