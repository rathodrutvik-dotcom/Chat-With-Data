# Chat with Your Data

An AI-powered document question-answering tool that enables you to upload documents (PDF, DOCX, XLSX) and ask questions. The application uses RAG (Retrieval-Augmented Generation) to provide contextual answers with citations from your documents.

## Project Overview

This application combines document processing, vector embeddings, and LLM capabilities to create a conversational interface for your documents. Key features include:

- **Document Upload**: Support for PDF, DOCX, and XLSX files
- **Persistent Conversations**: Chat history is saved automatically and survives page refreshes
- **Multiple Sessions**: Manage multiple document collections with independent chat histories
- **RAG Pipeline**: Uses Chroma vector store, LangChain, and Google Gemini LLM for accurate, contextual responses
- **Session Management**: Switch between different document sessions seamlessly

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher (for React frontend)
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

### Installation Steps

#### Step 1: Clone the Repository

```bash
git clone https://github.com/[your_repo_name]
cd Chat-With-Data
```

#### Step 2: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# API Keys
GEMINI_API_KEY=your_gemini_api_key_here

# Model Selection (optional, defaults shown)
GEMINI_MODEL=gemini-2.5-flash-lite
```

#### Step 3: Set Up Python Backend

**Create and activate virtual environment:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**Install Python dependencies:**

```bash
pip install -r requirements.txt
```

#### Step 4: Set Up React Frontend

**Navigate to frontend directory and install dependencies:**

```bash
cd frontend
npm install
cd ..
```

### Running the Application

#### Option 1: Quick Start (Recommended)

Use the provided startup script to run both backend and frontend together:

```bash
./start.sh
```
wait upto 5 seconds to ready backend server and then visit  `http://localhost:5173`, your app is ready!

This will start:
- Python API server on `http://localhost:8000`
- React frontend on `http://localhost:5173`

#### Option 2: Manual Start

**Terminal 1 - Start Python API Server:**

```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
cd src
python api_server.py
```

The API server will run on `http://localhost:8000`

**Terminal 2 - Start React Frontend:**

```bash
cd frontend
npm run dev
```

The React app will run on `http://localhost:5173`

**Access the application:** Open your browser and navigate to `http://localhost:5173`

#### Option 3: Testing Backend Only (Gradio UI)

For testing the Python backend independently without the React frontend:

```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
cd src
python main.py
```

This starts a Gradio test interface on `http://127.0.0.1:7860`

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

### View Database

```bash
sqlite3 src/logs/chat_history.db
```

## Technology Stack

- **Frontend**: React + Vite + Tailwind CSS
- **Backend**: Python FastAPI (API Server) + Gradio (Testing UI)
- **LLM**: Google Gemini (gemini-2.5-flash-lite default)
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
