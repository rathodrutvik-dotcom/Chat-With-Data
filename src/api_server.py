"""
FastAPI REST API server for Chat with Documents RAG application.
This server provides REST endpoints for the React frontend.
"""
import os
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from models.session_manager import get_session_manager
from rag.pipeline import process_user_question, proceed_input

# Load environment variables
load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

# Initialize FastAPI app
app = FastAPI(
    title="Chat with Documents API",
    description="REST API for RAG-based document chat application",
    version="1.0.0"
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize session manager
session_manager = get_session_manager()

# Import DATA_DIR from config to ensure consistency
from config.settings import DATA_DIR


# Pydantic models for request/response
class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    session_id: str
    message: str
    

class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    role: str
    content: str
    timestamp: str


class SessionInfo(BaseModel):
    """Session information model."""
    session_id: str
    document_name: str
    last_updated: str
    message_count: int


class SessionCreate(BaseModel):
    """Response for session creation."""
    session_id: str
    document_name: str
    collection_name: str
    message: str


class MessageHistory(BaseModel):
    """Chat message model."""
    role: str
    content: str
    timestamp: Optional[str] = None


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Chat with Documents API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "sessions": "/api/sessions",
            "chat": "/api/chat",
            "upload": "/api/upload"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/sessions", response_model=List[SessionInfo])
async def get_sessions():
    """Get all active sessions."""
    try:
        sessions = session_manager.get_all_sessions()
        result = []
        
        for session_id, doc_name, last_updated in sessions:
            # Get message count
            messages = session_manager.load_chat_history(session_id)
            result.append({
                "session_id": session_id,
                "document_name": doc_name,
                "last_updated": last_updated,
                "message_count": len(messages)
            })
        
        return result
    except Exception as e:
        logging.error(f"Error fetching sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/messages", response_model=List[MessageHistory])
async def get_session_messages(session_id: str):
    """Get chat history for a specific session."""
    try:
        # Check if session exists
        rag_session = session_manager.get_session(session_id)
        if not rag_session:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        # Load chat history
        messages = session_manager.load_chat_history(session_id)
        return [
            {
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg.get("timestamp")
            }
            for msg in messages
        ]
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching messages for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/{session_id}/clear")
async def clear_session_chat(session_id: str):
    """Clear chat history for a session."""
    try:
        success = session_manager.clear_session_chat(session_id)
        if success:
            return {"message": "Chat history cleared", "session_id": session_id}
        raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error clearing session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its data."""
    try:
        success = session_manager.delete_session(session_id)
        if success:
            return {"message": "Session deleted successfully", "session_id": session_id}
        raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload", response_model=SessionCreate)
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Upload and process documents to create a new session.
    Accepts PDF, DOCX, and XLSX files.
    """
    import tempfile
    import os
    
    temp_dir = None
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        # Create a temporary directory for uploaded files
        temp_dir = tempfile.mkdtemp()
        
        # Save uploaded files to temporary directory
        temp_files = []
        for file in files:
            # Validate file type
            allowed_extensions = [".pdf", ".docx", ".xlsx"]
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in allowed_extensions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file type: {file.filename}. Allowed: PDF, DOCX, XLSX"
                )
            
            # Save to temporary location
            temp_path = Path(temp_dir) / file.filename
            with open(temp_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # Create a file-like object with name attribute (compatible with Gradio interface)
            class FileObject:
                def __init__(self, path):
                    self.name = str(path)
            
            temp_files.append(FileObject(temp_path))
        
        # Process documents using existing pipeline
        # This will save files properly to DATA_DIR with collection naming
        rag_session, collection_name, doc_name = proceed_input(temp_files)
        
        # Create session
        session_id = session_manager.create_session(
            rag_session,
            doc_name,
            collection_name
        )
        
        return {
            "session_id": session_id,
            "document_name": doc_name,
            "collection_name": collection_name,
            "message": f"Documents processed successfully: {doc_name}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error processing upload: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing documents: {str(e)}")
    finally:
        # Clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
                logging.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logging.warning(f"Could not clean up temp directory {temp_dir}: {e}")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message and get a response from the RAG system.
    """
    try:
        session_id = request.session_id
        message = request.message.strip()
        
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Get RAG session
        rag_session = session_manager.get_session(session_id)
        if not rag_session:
            raise HTTPException(
                status_code=404,
                detail="Session not found or expired. Please reprocess documents."
            )
        
        # Save user message
        session_manager.save_message(session_id, "user", message)
        
        # Load chat history for context
        chat_history = session_manager.load_chat_history(session_id)
        history_for_context = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in chat_history
        ]
        
        # Get response from RAG
        answer = process_user_question(message, rag_session, history_for_context)
        
        # Save assistant response
        session_manager.save_message(session_id, "assistant", answer)
        
        return {
            "role": "assistant",
            "content": answer,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@app.get("/api/sessions/{session_id}/info")
async def get_session_info(session_id: str):
    """Get detailed information about a session."""
    try:
        session_info = session_manager.get_session_info(session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check if session is loaded in memory
        rag_session = session_manager.get_session(session_id)
        is_active = rag_session is not None
        
        # Get message count
        messages = session_manager.load_chat_history(session_id)
        
        return {
            "session_id": session_id,
            "document_name": session_info["document_name"],
            "collection_name": session_info["collection_name"],
            "created_at": session_info.get("created_at"),
            "last_updated": session_info.get("last_updated"),
            "is_active": is_active,
            "message_count": len(messages)
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# Run server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
