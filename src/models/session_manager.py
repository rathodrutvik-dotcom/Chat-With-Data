"""
Session manager for handling multiple document chat sessions.
"""
import logging
import uuid
import shutil
import glob
import chromadb
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from langchain_chroma import Chroma
from langchain_core.documents import Document

from config.settings import EMBEDDING_STORE_DIR, DATA_DIR, embedding_model
from models.chat_storage import get_chat_storage
from models.session import RagSession
from prompts.system_prompt import read_system_prompt
from rag.pipeline import build_rag_chain
from retrieval.ranking import SparseIndex
from vectorstore.chroma_store import get_chroma_settings


class SessionManager:
    """Manages multiple RAG sessions for different documents."""

    def __init__(self):
        """Initialize session manager."""
        self.storage = get_chat_storage()
        self.active_sessions: Dict[str, RagSession] = {}
        logging.info("SessionManager initialized")

    def create_session(
        self,
        rag_session: RagSession,
        document_name: str,
        collection_name: str
    ) -> str:
        """
        Create a new session for a document.

        Args:
            rag_session: RAG session object
            document_name: Name of the document(s)
            collection_name: Vector store collection name

        Returns:
            session_id: Unique identifier for the session
        """
        session_id = str(uuid.uuid4())

        # Update RAG session with metadata
        rag_session.session_id = session_id
        rag_session.document_name = document_name
        rag_session.collection_name = collection_name

        # Store in memory
        self.active_sessions[session_id] = rag_session

        # Persist to database
        self.storage.create_session(session_id, document_name, collection_name)

        logging.info("Created session %s for document: %s", session_id, document_name)
        return session_id

    def get_session(self, session_id: str) -> Optional[RagSession]:
        """Get a RAG session by ID, loading it if necessary."""
        # Check if already in memory
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]

        # Try to restore from disk
        session_info = self.storage.get_session(session_id)
        if session_info:
            try:
                restored_session = self._restore_session(session_info)
                if restored_session:
                    self.active_sessions[session_id] = restored_session
                    logging.info("Restored session %s from disk", session_id)
                    return restored_session
            except Exception as e:
                logging.warning("Could not restore session %s: %s", session_id, e)

        return None

    def _restore_session(self, session_info: dict) -> Optional[RagSession]:
        """
        Attempt to restore a RAG session from its persisted vector store.

        Args:
            session_info: Session metadata from database

        Returns:
            RagSession if successful, None otherwise
        """
        try:
            collection_name = session_info['collection_name']
            session_dir = EMBEDDING_STORE_DIR / collection_name

            # Check if vector store directory exists
            if not session_dir.exists():
                logging.warning("Vector store directory not found: %s", session_dir)
                return None

            # Restore vector store
            client = chromadb.PersistentClient(
                path=str(session_dir),
                settings=get_chroma_settings(),
            )

            vectorstore = Chroma(
                client=client,
                collection_name=collection_name,
                embedding_function=embedding_model,
            )

            # Restore sparse index from vector store documents
            docs = vectorstore.get()
            if not docs or not docs.get('documents'):
                logging.warning("No documents found in vector store for session %s", session_info['session_id'])
                return None

            # Recreate documents for sparse index
            restored_docs = [
                Document(page_content=content, metadata=metadata if metadata else {})
                for content, metadata in zip(docs['documents'], docs['metadatas'])
            ]

            sparse_index = SparseIndex(restored_docs)
            system_prompt = read_system_prompt("custom.yaml")
            rag_chain = build_rag_chain(system_prompt)

            # Create restored session
            restored_session = RagSession(
                rag_chain=rag_chain,
                vectorstore=vectorstore,
                sparse_index=sparse_index,
                session_id=session_info['session_id'],
                document_name=session_info['document_name'],
                collection_name=collection_name
            )

            logging.info("Successfully restored session: %s", session_info['document_name'])
            return restored_session

        except Exception as e:
            logging.error("Error restoring session: %s", e, exc_info=True)
            return None

    def set_session(self, session_id: str, rag_session: RagSession):
        """Store or update a RAG session."""
        self.active_sessions[session_id] = rag_session

    def get_all_sessions(self) -> List[Tuple[str, str, str]]:
        """
        Get all active sessions.

        Returns:
            List of tuples: (session_id, display_name, last_updated)
        """
        sessions = self.storage.get_all_active_sessions()
        return [
            (s["session_id"], s["display_name"], s["last_updated"])
            for s in sessions
        ]

    def load_chat_history(self, session_id: str) -> List[dict]:
        """Load chat history for a session."""
        messages = self.storage.get_messages(session_id)
        return messages

    def save_message(self, session_id: str, role: str, content: str) -> bool:
        """Save a message to the session."""
        return self.storage.add_message(session_id, role, content)

    def clear_session_chat(self, session_id: str) -> bool:
        """Clear chat messages for a session."""
        return self.storage.clear_session_messages(session_id)

    def rename_session(self, session_id: str, new_name: str) -> bool:
        """Rename a chat session.

        Args:
            session_id: ID of the session to rename
            new_name: New display name for the session

        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.storage.rename_session(session_id, new_name)
            if success:
                # Update in-memory session if loaded
                if session_id in self.active_sessions:
                    session_info = self.storage.get_session(session_id)
                    if session_info:
                        # Update both document_name and display_name
                        self.active_sessions[session_id].document_name = session_info['display_name']
                        logging.info("Updated in-memory session name for %s", session_id)
            return success
        except Exception as e:
            logging.error("Error renaming session %s: %s", session_id, e)
            return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its embedding store."""
        try:
            # Get session info to find the collection name
            session_info = self.storage.get_session(session_id)

            # Remove from active sessions
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]

            # Delete embedding store directory and uploaded files
            if session_info and session_info.get('collection_name'):
                collection_name = session_info['collection_name']

                # Delete embedding store directory
                store_dir = EMBEDDING_STORE_DIR / collection_name
                if store_dir.exists():
                    try:
                        shutil.rmtree(store_dir)
                        logging.info("Deleted embedding store for session %s at %s", session_id, store_dir)
                    except Exception as e:
                        logging.warning("Could not delete embedding store at %s: %s", store_dir, e)

                # Delete uploaded document files from DATA_DIR
                # Files are named as: {collection_name}-{idx}.{ext}
                try:
                    data_files = glob.glob(str(DATA_DIR / f"{collection_name}-*"))
                    for file_path in data_files:
                        try:
                            Path(file_path).unlink()
                            logging.info("Deleted uploaded file: %s", file_path)
                        except Exception as e:
                            logging.warning("Could not delete file %s: %s", file_path, e)

                    if data_files:
                        logging.info("Deleted %d uploaded file(s) for session %s", len(data_files), session_id)
                except Exception as e:
                    logging.warning("Error deleting uploaded files for session %s: %s", session_id, e)

            # Mark as inactive in database
            success = self.storage.delete_session(session_id)

            if success:
                logging.info("Successfully deleted session %s", session_id)

            return success

        except Exception as e:
            logging.error("Error deleting session %s: %s", session_id, e)
            return False

    def get_session_info(self, session_id: str) -> Optional[dict]:
        """Get session information from storage."""
        return self.storage.get_session(session_id)

    def add_documents_to_session(
        self,
        session_id: str,
        new_docs: list,
        new_original_filenames: List[str]
    ) -> bool:
        """Add new documents to an existing session.

        Args:
            session_id: ID of the session to update
            new_docs: List of processed document chunks to add
            new_original_filenames: List of original filenames being added

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get existing session
            rag_session = self.get_session(session_id)
            if not rag_session:
                logging.error("Session %s not found", session_id)
                return False

            # Add documents to existing vector store
            logging.info("Adding %d new chunks to session %s", len(new_docs), session_id)
            rag_session.vectorstore.add_documents(new_docs)

            # Rebuild sparse index with combined documents
            existing_docs = rag_session.vectorstore.get()
            if existing_docs and existing_docs.get('documents'):
                all_docs = [
                    Document(page_content=content, metadata=metadata if metadata else {})
                    for content, metadata in zip(existing_docs['documents'], existing_docs['metadatas'])
                ]
                # Recreate sparse index with all documents
                rag_session.sparse_index = SparseIndex(all_docs)
                logging.info("Rebuilt sparse index with %d total documents", len(all_docs))

            # Update database to track new documents
            success = self.storage.append_documents_to_session(session_id, new_original_filenames)

            if success:
                logging.info(
                    "Successfully added %d documents to session %s",
                    len(new_original_filenames), session_id
                )

            return success

        except Exception as e:
            logging.error("Error adding documents to session %s: %s", session_id, e, exc_info=True)
            return False


# Global instance
_session_manager = None


def get_session_manager() -> SessionManager:
    """Get or create the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


__all__ = ["SessionManager", "get_session_manager"]
