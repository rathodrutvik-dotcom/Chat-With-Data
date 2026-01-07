# Chat with Your Data

An AI-powered document question-answering tool that enables you to upload documents (PDF, DOCX, XLSX) and ask questions. The application uses RAG (Retrieval-Augmented Generation) to provide contextual answers with citations from your documents.

## Project Overview

This application combines document processing, vector embeddings, and LLM capabilities to create a conversational interface for your documents. Key features include:

- **Document Upload**: Support for PDF, DOCX, and XLSX files
- **Persistent Conversations**: Chat history is saved automatically and survives page refreshes
- **Multiple Sessions**: Manage multiple document collections with independent chat histories
- **RAG Pipeline**: Uses Chroma vector store, LangChain, and configurable LLM (Groq or Gemini) for accurate, contextual responses
- **Flexible LLM Support**: Choose between Groq or Google Gemini as your LLM provider
- **Session Management**: Switch between different document sessions seamlessly

## Architecture

The application follows a modular architecture:

- **UI Layer**: Gradio interface for document upload and chat
- **RAG Pipeline**: Document processing, chunking, embedding, and retrieval
- **Session Management**: Manages multiple document sessions and chat histories
- **Storage**: SQLite database for persistent chat storage, Chroma for vector embeddings

## Getting Started

### Prerequisites

- Python 3.8 or higher
- At least one LLM API key:
  - Groq API key ([Get one here](https://console.groq.com))
  - OR Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))
- (Optional) Ngrok auth token for public sharing

### Installation Steps

#### Step 1: Clone the Repository

```bash
git clone https://github.com/Tokir-Vora/chat-with-your-data.git
cd chat-with-your-data
```

#### Step 2: Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

#### Step 4: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# API Keys (at least one required)
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# LLM Provider Configuration
USE_GROQ=true      # Set to true to enable Groq
USE_GEMINI=false   # Set to true to enable Gemini

# Model Selection (optional, defaults shown)
GROQ_MODEL=llama-3.1-8b-instant
GEMINI_MODEL=gemini-2.0-flash-exp

# Optional
NGROK_AUTH_TOKEN=<your_ngrok_token>
```

**LLM Provider Priority:**
- If both `USE_GROQ` and `USE_GEMINI` are enabled, Gemini will be used by default
- At least one provider must be enabled
- You only need the API key for the provider you're using

#### Step 5: Run the Application

```bash
cd src
python main.py
```

The application will start and provide a local URL (typically `http://127.0.0.1:7860`).

## Project Structure

```
Chat-With-Data/
├── src/
│   ├── main.py                 # Gradio UI and application entry point
│   ├── models/                 # Session and storage management
│   │   ├── session.py         # Session data models
│   │   ├── session_manager.py # Session orchestration
│   │   └── chat_storage.py    # Database operations
│   ├── rag/
│   │   └── pipeline.py        # RAG processing pipeline
│   ├── ingestion/             # Document loading and chunking
│   ├── retrieval/             # Query processing and ranking
│   ├── vectorstore/           # Chroma vector store integration
│   └── logs/
│       └── chat_history.db    # SQLite database (auto-created)
├── data/                      # Uploaded documents storage
├── embedding_store/           # Chroma vector embeddings
├── requirements.txt           # Python dependencies
└── .env                       # Environment variables
```

## Usage

1. **Upload Documents**: Click "Upload New Documents" and select your files
2. **Name Your Session**: Optionally provide a descriptive name (e.g., "Q4 Financial Reports")
3. **Process Documents**: Click "Process Documents" to index your files
4. **Start Chatting**: Select a session from the dropdown and ask questions
5. **Switch Sessions**: Use the dropdown to switch between different document collections

## Features

- ✅ Persistent chat history across page refreshes
- ✅ Multiple document sessions with independent contexts
- ✅ Automatic message saving
- ✅ Session switching and management
- ✅ Custom document naming
- ✅ Vector-based semantic search
- ✅ Contextual answers with citations

## Additional Tools

### Generate Flake8 Report

```bash
./generate_flake8_reports.sh
```

### View Database

```bash
sqlite3 src/logs/chat_history.db
```

## Technology Stack

- **UI**: Gradio
- **LLM**: Configurable (Groq or Google Gemini)
  - Groq: llama-3.1-8b-instant (default)
  - Gemini: gemini-2.0-flash-exp (default)
- **Vector Store**: Chroma
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **Framework**: LangChain
- **Database**: SQLite

## Notes

- Documents are stored in `data/` directory
- Embeddings persist in `embedding_store/` directory
- Chat history is stored in `src/logs/chat_history.db`
- Processing time increases with larger files
- Internet connection required for LLM API access
- You can switch between Groq and Gemini by updating the `.env` file
