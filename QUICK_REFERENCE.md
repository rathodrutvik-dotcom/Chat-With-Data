# Quick Reference Guide

## Implementation Overview

### Architecture Flow

```
User Interface (Gradio)
        ↓
Session Manager (Orchestration)
        ↓
RAG Pipeline (Processing)
        ↓
Vector Store (Chroma) + Database (SQLite)
```

### Key Components

1. **Session Manager**: Manages multiple document sessions and coordinates between UI and storage
2. **RAG Pipeline**: Handles document processing, chunking, embedding, retrieval, and response generation
3. **Chat Storage**: SQLite database for persistent conversation history
4. **Vector Store**: Chroma for semantic search and document retrieval

### Data Flow

1. **Document Upload** → Files saved to `data/` directory
2. **Document Processing** → Loaded, chunked, and embedded using sentence transformers
3. **Vector Storage** → Embeddings stored in Chroma vector store
4. **Query Processing** → User question processed through RAG pipeline
5. **Retrieval** → Relevant chunks retrieved using MMR (Maximal Marginal Relevance)
6. **Response Generation** → Gemini LLM generates contextual answer with citations
7. **Storage** → Conversation saved to SQLite database

## Workflows

### Basic Workflow

```
Upload Document → Process → Chat → Messages Auto-Saved → Switch Session → Continue Chat
```

### Session Management Workflow

```
Create Session → Chat → Refresh Page → Select Session → History Loads → Continue
```

### Multi-Document Workflow

```
Upload Doc A → Process → Chat
Upload Doc B → Process → Chat
Switch to Doc A → Previous Chat Loads
Switch to Doc B → Previous Chat Loads
```

## Implementation Techniques

### Document Processing

- **Loaders**: Format-specific loaders for PDF, DOCX, XLSX
- **Chunking**: RecursiveCharacterTextSplitter for optimal chunk sizes
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2 for CPU-based embeddings
- **Storage**: Chroma vector store with persistent embeddings

### Retrieval Strategy

- **MMR Retrieval**: Maximal Marginal Relevance for diverse, relevant results
- **Query Rewriting**: Generates query variations for better retrieval
- **Reranking**: Cross-encoder model for improved relevance
- **Context Assembly**: Filters duplicates and formats context with metadata

### Session Management

- **Database Schema**: 
  - `sessions` table: Document metadata and session info
  - `messages` table: Conversation history with timestamps
- **State Management**: Hybrid approach (in-memory + persistent)
- **Auto-Save**: Messages saved immediately after user input and bot response
- **Auto-Load**: Chat history loads automatically when session is selected

## UI Components

| Component | Function |
|-----------|----------|
| Session Dropdown | View and switch between document sessions |
| File Upload | Upload PDF, DOCX, XLSX files |
| Document Name Input | Provide custom names for sessions |
| Process Documents | Index uploaded documents |
| Chat Interface | Interactive Q&A with documents |
| Refresh Button | Update session list |
| Clear Chat | Remove messages (keeps session) |
| Delete Session | Remove entire session |

## Common Workflows

### First Time User
1. Upload documents
2. (Optional) Name the session
3. Process documents
4. Start asking questions
5. Messages auto-save

### Returning User
1. Open application
2. Select session from dropdown
3. Previous chat history loads
4. Continue conversation

### Multiple Documents
1. Upload and process Document A
2. Chat about Document A
3. Upload and process Document B
4. Switch between sessions as needed
5. Each session maintains independent context

## Database Structure

**Sessions Table:**
- `session_id` (UUID)
- `document_name` (user-friendly name)
- `collection_name` (vector store collection)
- `created_at`, `last_updated` (timestamps)
- `is_active` (soft delete flag)

**Messages Table:**
- `message_id` (auto-increment)
- `session_id` (foreign key)
- `role` (user/assistant)
- `content` (message text)
- `timestamp` (when sent)

## Key Features

✅ **Persistent Storage**: SQLite database saves all conversations  
✅ **Multiple Sessions**: Separate chats for different documents  
✅ **Session Switching**: Dropdown menu for easy navigation  
✅ **Auto-Save**: Messages saved immediately  
✅ **Auto-Load**: History loads on session selection  
✅ **Page Refresh Safe**: Conversations survive refreshes  
✅ **Custom Naming**: Meaningful names for document collections  
✅ **Vector Search**: Semantic search for relevant context  

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Session not appearing | Click Refresh button |
| History not loading | Select session from dropdown |
| Can't send messages | Ensure session is selected |
| Upload fails | Verify file format (.pdf, .docx, .xlsx) |
| API error | Check GEMINI_API_KEY in .env file |

## File Locations

| Item | Path |
|------|-----|
| Main app | `src/main.py` |
| Database | `src/logs/chat_history.db` |
| Uploads | `data/` |
| Embeddings | `embedding_store/` |
| Config | `.env` |

## Quick Commands

```bash
# Start the app
python src/main.py

# View database
sqlite3 src/logs/chat_history.db
```
