# 📚 Chat with Documents - RAG Application

A powerful RAG (Retrieval-Augmented Generation) application that allows you to chat with your documents using AI. Now with **two interfaces**: the original Gradio interface and a modern ChatGPT-style React frontend!

## ✨ Features

### Core Functionality
- 📄 **Multi-format Support**: PDF, DOCX, and XLSX files
- 🤖 **AI-Powered Chat**: Intelligent responses using Groq LLM (Llama 3.3 70B)
- 🔍 **Advanced RAG Pipeline**: Hybrid search with dense + sparse retrieval
- 💾 **Session Management**: Persistent chat history and document sessions
- 🎯 **Context-Aware**: Remembers conversation history
- 🚀 **Fast & Accurate**: Cross-encoder reranking for better results

### Two User Interfaces

#### 1. **Gradio Interface** (Original)
- Simple, functional web UI
- Built-in file upload and chat
- Runs on port 7000
- Perfect for quick testing

#### 2. **React Frontend** (New! 🎉)
- Modern ChatGPT-like interface
- Smooth animations and transitions
- Mobile-responsive design
- Drag-and-drop file upload
- Real-time typing indicators
- Markdown and code syntax highlighting
- Session management sidebar
- Dark theme support

## 🏗️ Architecture

```
┌─────────────────┐
│  React Frontend │ ← Modern ChatGPT UI (Port 5173)
│     (Vite)      │
└────────┬────────┘
         │
         │ REST API
         ▼
┌─────────────────┐
│ FastAPI Server  │ ← New API Backend (Port 8000)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   RAG Engine    │ ← Existing pipeline
│  - Vector Store │
│  - LLM Chain    │
│  - Embeddings   │
└─────────────────┘

┌─────────────────┐
│  Gradio App     │ ← Original UI (Port 7000)
└─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+
- npm or yarn
- GROQ API Key ([Get one here](https://console.groq.com))

### 1. Clone and Setup

```bash
# Navigate to project
cd Chat-With-Data

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your GROQ API key
nano .env  # or use your preferred editor
```

```env
GROQ_API_KEY=your_actual_api_key_here
```

### 3. Setup Frontend

```bash
cd frontend
npm install
cd ..
```

### 4. Start the Application

#### Option A: Use the Quick Start Script (Recommended)

```bash
chmod +x start.sh
./start.sh
```

This starts both FastAPI backend and React frontend automatically!

#### Option B: Manual Start

**Terminal 1 - FastAPI Backend:**
```bash
cd src
python api_server.py
```

**Terminal 2 - React Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 3 - Gradio App (Optional):**
```bash
cd src
python main.py
```

### 5. Access the Application

- **React UI**: http://localhost:5173 (Modern interface)
- **Gradio UI**: http://localhost:7000 (Original interface)
- **API Docs**: http://localhost:8000/docs (Swagger UI)

## 📖 Usage Guide

### Using the React Frontend

1. **Upload Documents**
   - Click "New Chat" button
   - Drag & drop files or click to browse
   - Upload PDF, DOCX, or XLSX files
   - Wait for processing (progress bar shown)

2. **Chat with Your Documents**
   - Type your question in the input box
   - Press Enter to send (Shift+Enter for new line)
   - AI responds with contextual answers
   - All messages auto-saved

3. **Manage Sessions**
   - View all sessions in left sidebar
   - Click to switch between sessions
   - Delete sessions with trash icon
   - See message count and last update time

### Using the Gradio Interface

1. Upload documents using the file upload component
2. Click "Process Documents"
3. Type questions in the chat input
4. View responses in the chatbot interface

## 🎨 Frontend Features

### Modern UI Components

- **Sidebar**: Session management with search and filters
- **Chat Area**: Smooth scrolling with message grouping
- **Message Input**: Auto-resize with keyboard shortcuts
- **File Upload**: Drag-and-drop with progress tracking
- **Typing Indicator**: Shows when AI is thinking
- **Error Handling**: User-friendly error messages

### Responsive Design

- Desktop: Full sidebar with multi-column layout
- Tablet: Collapsible sidebar
- Mobile: Bottom navigation with full-screen chat

### Markdown Support

The chat supports rich formatting:
- **Bold** and *italic* text
- Code blocks with syntax highlighting
- Lists (ordered and unordered)
- Links and quotes
- Math equations (KaTeX)

## 🛠️ Technology Stack

### Backend
- **Python 3.8+**
- **FastAPI**: REST API framework
- **LangChain**: RAG orchestration
- **Groq**: LLM inference (Llama 3.3 70B)
- **ChromaDB**: Vector database
- **HuggingFace**: Embeddings
- **Gradio**: Original UI

### Frontend
- **React 18**: UI framework
- **Vite**: Build tool
- **Tailwind CSS**: Styling
- **Axios**: HTTP client
- **React Markdown**: Markdown rendering
- **React Icons**: Icons library
- **date-fns**: Date formatting

## 📁 Project Structure

```
Chat-With-Data/
├── src/                        # Backend code
│   ├── api_server.py          # FastAPI REST API (NEW)
│   ├── main.py                # Gradio app
│   ├── config/                # Configuration
│   ├── ingestion/             # Document processing
│   ├── models/                # Session management
│   ├── rag/                   # RAG pipeline
│   ├── retrieval/             # Search & ranking
│   ├── vectorstore/           # Vector DB
│   └── prompts/               # System prompts
│
├── frontend/                   # React frontend (NEW)
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── context/           # State management
│   │   ├── services/          # API client
│   │   └── App.jsx            # Main app
│   ├── package.json
│   └── vite.config.js
│
├── data/                       # Uploaded files
├── embedding_store/            # Vector storage
├── requirements.txt            # Python dependencies
├── start.sh                   # Quick start script
├── FRONTEND_SETUP.md          # Detailed setup guide
└── README.md                  # This file
```

## 🔌 API Endpoints

### Session Management
- `GET /api/sessions` - List all sessions
- `GET /api/sessions/{id}/messages` - Get chat history
- `GET /api/sessions/{id}/info` - Get session details
- `POST /api/sessions/{id}/clear` - Clear chat
- `DELETE /api/sessions/{id}` - Delete session

### Document Processing
- `POST /api/upload` - Upload and process documents

### Chat
- `POST /api/chat` - Send message and get response

### Utility
- `GET /api/health` - Health check
- `GET /api/` - API information

Full API documentation: http://localhost:8000/docs

## 🎯 RAG Pipeline Details

### Document Processing
1. File upload and validation
2. Text extraction (PDF/DOCX/XLSX)
3. Intelligent chunking
4. Embedding generation
5. Vector storage (ChromaDB)

### Query Processing
1. Query rewriting for clarity
2. Query expansion (multiple variations)
3. Hybrid retrieval (dense + sparse)
4. Cross-encoder reranking
5. Context assembly
6. LLM generation with history

### Features
- **Hybrid Search**: Combines semantic and keyword search
- **Query Rewriting**: Improves ambiguous queries
- **Context Grounding**: Uses chat history for follow-ups
- **Smart Chunking**: Preserves document structure
- **Deduplication**: Filters similar results

## 🔧 Configuration

### Environment Variables

```env
# Required
GROQ_API_KEY=your_api_key

# Optional
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
GRADIO_HOST=0.0.0.0
GRADIO_PORT=7000
```

### RAG Parameters

Edit `src/config/settings.py`:

```python
DENSE_CANDIDATE_K = 30        # Dense retrieval results
RERANK_TOP_K = 7             # Reranking top results
FINAL_CONTEXT_DOCS = 5       # Final context documents
SIMILARITY_THRESHOLD = 0.82   # Similarity cutoff
```

## 🐛 Troubleshooting

### Common Issues

**1. Port Already in Use**
```bash
# Kill process on port 8000
lsof -i :8000
kill -9 <PID>
```

**2. API Key Error**
- Check `.env` file exists
- Verify API key is correct
- Ensure no quotes around key

**3. Frontend Can't Connect**
- Verify backend is running
- Check CORS settings
- Look at browser console

**4. Session Not Found**
- Backend may have restarted
- Reupload documents
- Check logs in `src/logs/`

**5. Slow Responses**
- Check network connection
- Verify Groq API status
- Reduce document size

For detailed troubleshooting, see [FRONTEND_SETUP.md](FRONTEND_SETUP.md)

## 📚 Documentation

- **[Frontend Setup Guide](frontend/README.md)**: React app details
- **[Complete Setup Guide](FRONTEND_SETUP.md)**: Full installation guide
- **[API Documentation](http://localhost:8000/docs)**: Interactive API docs
- **[Quick Reference](QUICK_REFERENCE.md)**: Quick tips and commands

## 🚢 Deployment

### Backend
- Use Docker for containerization
- Deploy to AWS, GCP, or Azure
- Consider using Gunicorn/Uvicorn workers

### Frontend
- Build: `cd frontend && npm run build`
- Deploy to Vercel, Netlify, or S3
- Configure environment variables

### Production Checklist
- [ ] Set production API keys
- [ ] Configure CORS properly
- [ ] Enable HTTPS
- [ ] Add rate limiting
- [ ] Set up monitoring
- [ ] Configure backups

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- **Groq** for fast LLM inference
- **LangChain** for RAG framework
- **HuggingFace** for embeddings
- **FastAPI** for modern Python APIs
- **React** and **Vite** for frontend

## 📞 Support

- 📧 Email: support@example.com
- 💬 Discord: [Join our community](#)
- 📖 Docs: [Full Documentation](#)
- 🐛 Issues: [GitHub Issues](#)

## 🎉 What's New in This Version

### ✨ New Features
- 🎨 Modern ChatGPT-like React interface
- 🔌 RESTful API with FastAPI
- 📱 Mobile-responsive design
- 🌙 Dark theme support (coming soon)
- 📊 Session analytics
- 🔄 Real-time updates

### 🔧 Improvements
- Better error handling
- Improved session persistence
- Faster document processing
- Enhanced UI/UX
- Better mobile experience

### 🐛 Bug Fixes
- Fixed session restoration issues
- Improved memory management
- Better error messages
- Fixed chat history loading

---

**Made with ❤️ for document intelligence**

**Star ⭐ this repo if you find it useful!**
