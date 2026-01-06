# Visual Guide - Understanding Your Application 📊

## Simple Architecture Diagram

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                 YOUR COMPUTER                      ┃
┃                                                    ┃
┃  ┌──────────────────────────────────────────┐    ┃
┃  │      WEB BROWSER (Chrome/Firefox)        │    ┃
┃  │                                          │    ┃
┃  │  ┌────────────────────────────────────┐ │    ┃
┃  │  │   React Frontend UI                │ │    ┃
┃  │  │   (JavaScript runs here)           │ │    ┃
┃  │  │   http://localhost:5173           │ │    ┃
┃  │  │                                    │ │    ┃
┃  │  │   📱 ChatGPT-like Interface       │ │    ┃
┃  │  │   ✉️  Upload Documents            │ │    ┃
┃  │  │   💬 Chat with AI                 │ │    ┃
┃  │  │   📋 View History                 │ │    ┃
┃  │  └────────┬───────────────────────────┘ │    ┃
┃  │           │                              │    ┃
┃  └───────────┼──────────────────────────────┘    ┃
┃              │                                    ┃
┃              │ HTTP API Calls                    ┃
┃              │ (fetch/axios)                     ┃
┃              ▼                                    ┃
┃  ┌────────────────────────────────────────────┐  ┃
┃  │   FastAPI Backend Server                   │  ┃
┃  │   (Python runs here)                       │  ┃
┃  │   http://localhost:8000                   │  ┃
┃  │                                            │  ┃
┃  │   🔧 RAG Pipeline                         │  ┃
┃  │   🤖 AI/ML Processing                     │  ┃
┃  │   💾 Session Management                   │  ┃
┃  │   📊 Vector Embeddings                    │  ┃
┃  └────────────────────────────────────────────┘  ┃
┃                                                    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

---

## How Data Flows

```
USER UPLOADS A DOCUMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. User clicks "Upload" in React UI
   │
   ├─► React component (FileUpload.jsx)
   │
   ├─► API service (api.js) prepares request
   │
   ├─► HTTP POST to http://localhost:8000/api/upload
   │
   ├─► FastAPI receives file (api_server.py)
   │
   ├─► RAG pipeline processes document
   │   ├─ Load document
   │   ├─ Chunk into pieces
   │   ├─ Create embeddings
   │   └─ Store in vector database
   │
   ├─► Response sent back to React
   │
   └─► UI updates with success message
```

```
USER SENDS A CHAT MESSAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. User types message and presses Enter
   │
   ├─► React component (MessageInput.jsx)
   │
   ├─► API service sends POST to /api/chat
   │
   ├─► FastAPI backend:
   │   ├─ Query rewriting
   │   ├─ Vector search for relevant chunks
   │   ├─ Rank results
   │   ├─ Send to LLM (Groq)
   │   └─ Get AI response
   │
   ├─► Stream response back to React
   │
   └─► UI displays message bubble-by-bubble
```

---

## File Structure Explained

```
YOUR PROJECT
│
├── 🚀 start.sh                    ← Run this to start everything
│
├── 📄 requirements.txt            ← Python packages list
│
├── 🐍 PYTHON BACKEND (src/)
│   │
│   ├── api_server.py             ← FastAPI server (NEW!)
│   │   • Provides REST API
│   │   • Connects React to Python
│   │   • Endpoints: /upload, /chat, /sessions
│   │
│   ├── main.py                   ← Gradio app (Your original)
│   │   • Still works!
│   │   • Can run separately
│   │
│   ├── rag/pipeline.py           ← RAG processing
│   ├── models/session_manager.py ← Chat sessions
│   ├── vectorstore/              ← Vector database
│   └── ...                       ← Other Python modules
│
└── ⚛️  REACT FRONTEND (frontend/)
    │
    ├── package.json              ← Node.js packages list
    │
    ├── node_modules/             ← Installed packages (auto-generated)
    │   └── (DON'T TOUCH THIS!)
    │
    ├── index.html                ← Main HTML file
    │
    └── src/                      ← Your React code
        │
        ├── main.jsx              ← App entry point
        ├── App.jsx               ← Main React component
        │
        ├── components/           ← UI Components
        │   ├── Header.jsx        ← Top navigation bar
        │   ├── Sidebar.jsx       ← Left sidebar with sessions
        │   ├── ChatContainer.jsx ← Main chat area
        │   ├── MessageList.jsx   ← Shows all messages
        │   ├── MessageInput.jsx  ← Text input box
        │   ├── FileUpload.jsx    ← Document upload
        │   └── ...
        │
        ├── services/             ← Backend communication
        │   └── api.js            ← All API calls here
        │
        └── context/              ← State management
            └── ChatContext.jsx   ← Global app state
```

---

## Technology Stack Visual

```
┌─────────────────────────────────────────────────┐
│              FRONTEND STACK                     │
├─────────────────────────────────────────────────┤
│  Language:    JavaScript/JSX                    │
│  Framework:   React 18                          │
│  Build Tool:  Vite                              │
│  Styling:     TailwindCSS                       │
│  HTTP Client: Fetch API                         │
│  Runtime:     Node.js (development)             │
│  Package Mgr: npm                               │
└─────────────────────────────────────────────────┘
                      ▲
                      │ HTTP REST API
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│              BACKEND STACK                      │
├─────────────────────────────────────────────────┤
│  Language:    Python 3.11+                      │
│  Framework:   FastAPI                           │
│  AI/ML:       LangChain                         │
│  LLM:         Groq (Llama)                      │
│  Embeddings:  HuggingFace                       │
│  Vector DB:   ChromaDB                          │
│  Server:      Uvicorn                           │
│  Environment: Python venv                       │
│  Package Mgr: pip                               │
└─────────────────────────────────────────────────┘
```

---

## Environment Setup Comparison

### Python Backend Setup

```bash
# What you do
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install -r requirements.txt

# What gets created
venv/
├── bin/
│   ├── python        ← Python interpreter
│   ├── pip           ← Package manager
│   └── activate      ← Activation script
└── lib/
    └── python3.x/
        └── site-packages/   ← Installed packages
            ├── fastapi/
            ├── langchain/
            └── ...

# How to run
$ python api_server.py
```

### React Frontend Setup

```bash
# What you do
$ cd frontend
$ npm install

# What gets created
node_modules/
├── react/            ← React library
├── vite/             ← Build tool
├── tailwindcss/      ← CSS framework
└── ...               ← 1000+ packages!

# How to run
$ npm run dev
```

**Key Difference:**
- Python: You activate venv, then run Python
- Node.js: No activation needed, just run npm commands

---

## Port Numbers Explained

```
┌──────────────────────────────────────┐
│  http://localhost:5173              │  ← React Frontend (Dev Server)
│  • What you see in browser          │
│  • ChatGPT-like interface           │
│  • User interacts here              │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│  http://localhost:8000              │  ← FastAPI Backend (API Server)
│  • Python RAG pipeline              │
│  • AI processing                    │
│  • Database operations              │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│  http://localhost:8000/docs         │  ← API Documentation
│  • Interactive API tester           │
│  • See all endpoints                │
│  • Try requests manually            │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│  http://localhost:7000              │  ← Gradio App (Your original)
│  • Still works independently        │
│  • Can run: python src/main.py     │
└──────────────────────────────────────┘
```

---

## What Happens When You Run `./start.sh`

```
STEP 1: Check Prerequisites
━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Is Node.js installed?
✓ Is Python installed?
✓ Is npm available?

STEP 2: Setup Python Backend
━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Create venv (if doesn't exist)
✓ Activate venv
✓ Install Python packages (pip)

STEP 3: Setup React Frontend
━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Check node_modules (if doesn't exist)
✓ Install Node packages (npm install)
  └─ Downloads 1000+ packages!
  └─ Takes 2-5 minutes first time
  └─ Creates node_modules folder

STEP 4: Start Backend Server
━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Run: python src/api_server.py
✓ Starts on port 8000
✓ Wait for initialization
✓ Verify it's running

STEP 5: Start Frontend Server
━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Run: npm run dev (in frontend/)
✓ Starts on port 5173
✓ Opens browser automatically

STEP 6: You're Ready!
━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Frontend: http://localhost:5173
✓ Backend:  http://localhost:8000
✓ Start chatting!
```

---

## Common Confusions Cleared

### 1. "Do I need venv for React?"

```
❌ WRONG:
$ cd frontend
$ python3 -m venv venv    # NO! This won't work!
$ source venv/bin/activate
$ npm install              # npm is not in Python!

✅ RIGHT:
$ cd frontend
$ npm install              # That's it!
```

**Why?** React uses Node.js, not Python!

---

### 2. "Can I install React with pip?"

```
❌ WRONG:
$ pip install react        # This won't work!

✅ RIGHT:
$ npm install react        # Use npm for JavaScript packages
```

---

### 3. "Where are React packages installed?"

```
Python packages:
venv/lib/python3.x/site-packages/

React packages:
frontend/node_modules/
```

They're in DIFFERENT places!

---

### 4. "How do I restart the frontend?"

```
❌ WRONG:
$ cd frontend
$ source venv/bin/activate  # No venv for React!
$ python npm run dev        # npm is not Python!

✅ RIGHT:
$ cd frontend
$ npm run dev               # That's it!
```

---

## Quick Command Reference

| What You Want | Python Backend | React Frontend |
|---------------|----------------|----------------|
| **Setup** | `python3 -m venv venv` | Already setup (Node.js install) |
| **Activate** | `source venv/bin/activate` | Not needed |
| **Install Packages** | `pip install -r requirements.txt` | `npm install` |
| **Add Package** | `pip install package` | `npm install package` |
| **Run Server** | `python api_server.py` | `npm run dev` |
| **Package File** | `requirements.txt` | `package.json` |
| **Packages Folder** | `venv/lib/.../site-packages/` | `node_modules/` |
| **Port** | 8000 | 5173 |

---

## Success Checklist ✅

After running `./start.sh`, you should see:

```
✅ Node.js installed: v18.x.x
✅ npm installed: v9.x.x
✅ Python installed: Python 3.x.x
✅ Virtual environment activated
✅ Python dependencies installed
✅ Frontend dependencies installed
✅ Backend is ready
✅ Frontend server started

📱 React Frontend:   http://localhost:5173
🔌 FastAPI Backend:  http://localhost:8000
📚 API Documentation: http://localhost:8000/docs
```

If you see all of this - **YOU'RE READY!** 🎉

---

## Next Steps

1. Open http://localhost:5173 in your browser
2. You'll see a ChatGPT-like interface
3. Upload a document
4. Start asking questions!

**Enjoy your new frontend! 🚀**
