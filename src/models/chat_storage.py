"""
Chat storage module for persisting conversation history across sessions.
"""
import re
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class ChatStorage:
    """Manages persistent storage of chat sessions and messages."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize chat storage with SQLite database."""
        if db_path is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            db_path = project_root / "src" / "logs" / "chat_history.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        logging.info("ChatStorage initialized at %s", self.db_path)

    def _init_database(self):
        """Create database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Sessions table with documents column for multi-doc tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    document_name TEXT NOT NULL,
                    display_name TEXT,
                    collection_name TEXT NOT NULL,
                    documents TEXT DEFAULT '[]',
                    document_batches TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            """)

            # Add documents column if it doesn't exist (for existing databases)
            try:
                cursor.execute("ALTER TABLE sessions ADD COLUMN documents TEXT DEFAULT '[]'")
                logging.info("Added documents column to sessions table")
            except sqlite3.OperationalError:
                pass  # Column already exists

            # Add display_name column if it doesn't exist (for existing databases)
            try:
                cursor.execute("ALTER TABLE sessions ADD COLUMN display_name TEXT")
                logging.info("Added display_name column to sessions table")
            except sqlite3.OperationalError:
                pass  # Column already exists

            # Add document_batches column if it doesn't exist
            try:
                cursor.execute("ALTER TABLE sessions ADD COLUMN document_batches TEXT DEFAULT '[]'")
                logging.info("Added document_batches column to sessions table")
            except sqlite3.OperationalError:
                pass  # Column already exists

            # Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)

            # Index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_messages 
                ON messages(session_id, timestamp)
            """)

            conn.commit()
            logging.info("Database initialized successfully")

    def create_session(
        self,
        session_id: str,
        document_name: str,
        collection_name: str,
        documents: List[str] = None,
        display_name: str = None
    ) -> bool:
        """Create a new chat session with document tracking.

        Args:
            session_id: Unique session identifier
            document_name: Technical name for the session (cleaned)
            collection_name: Vector store collection name
            documents: List of original document filenames
            display_name: User-friendly display name (optional, defaults to document_name)
        """
        try:
            documents_json = json.dumps(documents or [])
            # Use display_name if provided, otherwise use document_name
            display = display_name if display_name else document_name
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sessions (session_id, document_name, display_name, collection_name, documents)
                    VALUES (?, ?, ?, ?, ?)
                """, (session_id, document_name, display, collection_name, documents_json))
                conn.commit()
                logging.info(
                    "Created session: %s for document: %s (display: %s) with %d documents",
                    session_id, document_name, display, len(documents or [])
                )
                return True
        except sqlite3.IntegrityError:
            logging.warning("Session %s already exists", session_id)
            return False
        except Exception as e:
            logging.error("Error creating session: %s", e)
            return False

    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session details by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT session_id, document_name, display_name, collection_name, documents, document_batches, created_at, last_updated
                    FROM sessions
                    WHERE session_id = ? AND is_active = 1
                """, (session_id,))

                row = cursor.fetchone()
                if row:
                    # Parse documents JSON
                    try:
                        documents = json.loads(row[4]) if row[4] else []
                    except (json.JSONDecodeError, TypeError):
                        documents = []

                    # Parse document_batches JSON
                    try:
                        document_batches = json.loads(row[5]) if row[5] else []
                    except (json.JSONDecodeError, TypeError):
                        document_batches = []

                    return {
                        "session_id": row[0],
                        "document_name": row[1],
                        "display_name": row[2] if row[2] else row[1],  # Fall back to document_name
                        "collection_name": row[3],
                        "documents": documents,
                        "document_batches": document_batches,
                        "created_at": row[6],
                        "last_updated": row[7]
                    }
                return None
        except Exception as e:
            logging.error("Error fetching session: %s", e)
            return None

    def get_all_active_sessions(self) -> List[dict]:
        """Get all active sessions."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT session_id, document_name, display_name, collection_name, created_at, last_updated
                    FROM sessions
                    WHERE is_active = 1
                    ORDER BY last_updated DESC
                """)

                sessions = []
                for row in cursor.fetchall():
                    sessions.append({
                        "session_id": row[0],
                        "document_name": row[1],
                        "display_name": row[2] if row[2] else row[1],  # Fall back to document_name
                        "collection_name": row[3],
                        "created_at": row[4],
                        "last_updated": row[5]
                    })
                return sessions
        except Exception as e:
            logging.error("Error fetching sessions: %s", e)
            return []

    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """Add a message to a session."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Add message
                cursor.execute("""
                    INSERT INTO messages (session_id, role, content)
                    VALUES (?, ?, ?)
                """, (session_id, role, content))

                # Update session's last_updated timestamp
                cursor.execute("""
                    UPDATE sessions
                    SET last_updated = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                """, (session_id,))

                conn.commit()
                return True
        except Exception as e:
            logging.error("Error adding message: %s", e)
            return False

    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[dict]:
        """Get all messages for a session."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                query = """
                    SELECT role, content, timestamp
                    FROM messages
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                """

                if limit:
                    query += f" LIMIT {limit}"

                cursor.execute(query, (session_id,))

                messages = []
                for row in cursor.fetchall():
                    messages.append({
                        "role": row[0],
                        "content": row[1],
                        "timestamp": row[2]
                    })
                return messages
        except Exception as e:
            logging.error("Error fetching messages: %s", e)
            return []

    def clear_session_messages(self, session_id: str) -> bool:
        """Clear all messages for a session."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM messages
                    WHERE session_id = ?
                """, (session_id,))
                conn.commit()
                logging.info("Cleared messages for session: %s", session_id)
                return True
        except Exception as e:
            logging.error("Error clearing messages: %s", e)
            return False

    def delete_session(self, session_id: str) -> bool:
        """Soft delete a session (mark as inactive)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sessions
                    SET is_active = 0
                    WHERE session_id = ?
                """, (session_id,))
                conn.commit()
                logging.info("Deleted session: %s", session_id)
                return True
        except Exception as e:
            logging.error("Error deleting session: %s", e)
            return False

    def rename_session(self, session_id: str, new_name: str) -> bool:
        """Rename a session's document_name.

        Args:
            session_id: Session to rename
            new_name: New display name for the session

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate new name
            if not new_name or not new_name.strip():
                logging.error("Invalid session name: empty or whitespace")
                return False

            # Store the original display name (with spaces)
            original_display_name = new_name.strip()

            # Clean the new name for technical use (same logic as file naming)
            clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', new_name.strip())
            clean_name = re.sub(r'_+', '_', clean_name)
            clean_name = clean_name.strip('_')

            if not clean_name:
                logging.error("Invalid session name after cleaning")
                return False

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check if new technical name already exists (excluding current session)
                cursor.execute("""
                    SELECT COUNT(*) FROM sessions
                    WHERE document_name = ? AND session_id != ? AND is_active = 1
                """, (clean_name, session_id))

                if cursor.fetchone()[0] > 0:
                    # Add suffix to make it unique (technical name only)
                    counter = 1
                    unique_name = f"{clean_name}_{counter}"
                    while True:
                        cursor.execute("""
                            SELECT COUNT(*) FROM sessions
                            WHERE document_name = ? AND session_id != ? AND is_active = 1
                        """, (unique_name, session_id))
                        if cursor.fetchone()[0] == 0:
                            clean_name = unique_name
                            break
                        counter += 1
                        unique_name = f"{clean_name}_{counter}"

                # Update both document_name (technical) and display_name (user-friendly)
                cursor.execute("""
                    UPDATE sessions
                    SET document_name = ?, display_name = ?
                    WHERE session_id = ?
                """, (clean_name, original_display_name, session_id))

                conn.commit()
                logging.info("Renamed session %s to: %s (display: %s)", session_id, clean_name, original_display_name)
                return True

        except Exception as e:
            logging.error("Error renaming session: %s", e)
            return False

    def update_session_timestamp(self, session_id: str) -> bool:
        """Update the last_updated timestamp for a session."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sessions
                    SET last_updated = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                """, (session_id,))
                conn.commit()
                return True
        except Exception as e:
            logging.error("Error updating session timestamp: %s", e)
            return False


    def append_documents_to_session(self, session_id: str, new_documents: List[str]) -> bool:
        """Append new documents to an existing session.

        Args:
            session_id: Session to update
            new_documents: List of new document filenames to add

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get current documents and batches
                cursor.execute("""
                    SELECT documents, document_batches
                    FROM sessions
                    WHERE session_id = ? AND is_active = 1
                """, (session_id,))

                row = cursor.fetchone()
                if not row:
                    logging.error("Session %s not found", session_id)
                    return False

                # Parse existing documents
                try:
                    current_docs = json.loads(row[0]) if row[0] else []
                    current_batches = json.loads(row[1]) if row[1] else []
                except (json.JSONDecodeError, TypeError):
                    current_docs = []
                    current_batches = []

                # Create new batch entry
                new_batch = {
                    "documents": new_documents,
                    "added_at": datetime.now().isoformat()
                }

                # Update lists
                updated_docs = current_docs + new_documents
                updated_batches = current_batches + [new_batch]

                # Update database
                cursor.execute("""
                    UPDATE sessions
                    SET documents = ?,
                        document_batches = ?,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                """, (json.dumps(updated_docs), json.dumps(updated_batches), session_id))

                conn.commit()
                logging.info(
                    "Appended %d documents to session %s (total: %d)",
                    len(new_documents), session_id, len(updated_docs)
                )
                return True

        except Exception as e:
            logging.error("Error appending documents to session: %s", e)
            return False

    def search_chats(self, query: str, limit: int = 20) -> List[dict]:
        """Search chats by title and content.
        
        Args:
            query: Search term
            limit: Maximum number of results
            
        Returns:
            List of matches including session info and snippets
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                results = []
                
                # 1. Search Session Titles
                cursor.execute("""
                    SELECT session_id, document_name, display_name, last_updated
                    FROM sessions
                    WHERE (document_name LIKE ? OR display_name LIKE ?) AND is_active = 1
                    ORDER BY last_updated DESC
                    LIMIT ?
                """, (f'%{query}%', f'%{query}%', limit))
                
                for row in cursor.fetchall():
                    results.append({
                        "session_id": row[0],
                        "document_name": row[1],
                        "display_name": row[2] if row[2] else row[1],
                        "match_type": "title",
                        "snippet": None,
                        "timestamp": row[3]
                    })
                    
                # 2. Search Messages
                remaining_limit = limit - len(results)
                if remaining_limit > 0:
                    cursor.execute("""
                        SELECT m.session_id, m.content, m.timestamp, s.document_name, s.display_name
                        FROM messages m
                        JOIN sessions s ON m.session_id = s.session_id
                        WHERE m.content LIKE ? AND s.is_active = 1
                        ORDER BY m.timestamp DESC
                        LIMIT ?
                    """, (f'%{query}%', remaining_limit))
                    
                    for row in cursor.fetchall():
                        # Create a snippet
                        content = row[1]
                        # Find the match index (case insensitive approximation for snippet)
                        idx = content.lower().find(query.lower())
                        if idx != -1:
                            start = max(0, idx - 40)
                            end = min(len(content), idx + 100)
                            snippet = ("..." if start > 0 else "") + content[start:end] + ("..." if end < len(content) else "")
                        else:
                            snippet = content[:100] + "..."
                        
                        results.append({
                            "session_id": row[0],
                            "document_name": row[3],
                            "display_name": row[4] if row[4] else row[3],
                            "match_type": "content",
                            "snippet": snippet,
                            "timestamp": row[2],
                            "message_timestamp": row[2]
                        })
                
                return results
        except Exception as e:
            logging.error("Error searching chats: %s", e)
            return []




# Global instance
_chat_storage = None


def get_chat_storage() -> ChatStorage:
    """Get or create the global chat storage instance."""
    global _chat_storage
    if _chat_storage is None:
        _chat_storage = ChatStorage()
    return _chat_storage


__all__ = ["ChatStorage", "get_chat_storage"]
