# Quick Start Guide - Chat With Data

## For Complete Beginners 👶

### What You Need to Install (One-Time Setup)

1. **Node.js** (Required for React frontend)
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install nodejs npm
   
   # Verify installation
   node -v  # Should show v18 or higher
   npm -v   # Should show v9 or higher
   ```

2. **Python 3** (Already installed on most Linux systems)
   ```bash
   python3 --version  # Should show Python 3.8 or higher
   ```

---

## Running the Application (Every Time)

### Option 1: One Command (Easiest!) ⭐

```bash
./start.sh
```

**That's it!** The script will:
- Install all dependencies automatically
- Start backend server (Python/FastAPI)
- Start frontend server (React/Vite)
- Open your browser to http://localhost:5173

---

### Option 2: Manual Control (If you want separate terminals)

**Terminal 1 - Backend:**
```bash
source venv/bin/activate
cd src
python api_server.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

---

## Using the Application

1. **Upload Documents**
   - Click "Upload Documents" button
   - Select PDF, TXT, DOCX, or MD files
   - Wait for processing (you'll see a progress indicator)

2. **Start Chatting**
   - Type your question in the input box
   - Press Enter or click Send
   - Get AI-powered answers from your documents

3. **Manage Sessions**
   - Create new chat sessions
   - Switch between sessions
   - Clear history when needed

4. **View Chat History**
   - All conversations are saved
   - Access previous chats anytime
   - Continue from where you left off

---

## Stopping the Application

Press `Ctrl+C` in the terminal running start.sh

---

## Troubleshooting

### "Node.js not found"
```bash
sudo apt install nodejs npm
```

### "Port already in use"
```bash
# Kill processes on ports
lsof -ti:8000 | xargs kill -9  # Backend
lsof -ti:5173 | xargs kill -9  # Frontend
```

### "Permission denied: ./start.sh"
```bash
chmod +x start.sh
```

### Frontend won't start
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Backend errors
```bash
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

---

## File Structure Overview

```
Chat-With-Data/
├── start.sh              # 🚀 Run this to start everything
├── requirements.txt      # Python dependencies
├── src/                  # Backend code (Python/FastAPI)
│   ├── api_server.py    # Main backend server
│   └── ...
└── frontend/             # Frontend code (React)
    ├── package.json     # Node.js dependencies
    └── src/             # React components
        ├── App.jsx      # Main app
        └── components/  # UI components
```

---

## URLs to Remember

| Service | URL | Description |
|---------|-----|-------------|
| Frontend (UI) | http://localhost:5173 | Main application interface |
| Backend (API) | http://localhost:8000 | FastAPI backend server |
| API Documentation | http://localhost:8000/docs | Interactive API docs |

---

## Common Questions

**Q: What's the difference between backend and frontend?**
- Backend = Python server doing AI/RAG processing
- Frontend = React UI you see in browser

**Q: Do I need to run npm install every time?**
- No! Only first time. The start.sh script handles it.

**Q: Can I edit files while servers are running?**
- Yes! Both auto-reload when you save changes.

**Q: Where are my uploaded files stored?**
- In `data/` folder (backend side)
- Vector embeddings in `embedding_store/`

**Q: How do I add new Python packages?**
```bash
source venv/bin/activate
pip install package-name
pip freeze > requirements.txt
```

**Q: How do I add new React packages?**
```bash
cd frontend
npm install package-name
```

---

## Need Help?

1. Check `FRONTEND_SETUP.md` for detailed setup instructions
2. Check `README.md` for full documentation
3. Check backend logs in `src/logs/`
4. Check browser console (F12) for frontend errors

---

**Ready to start? Run:**
```bash
./start.sh
```

**Then open:** http://localhost:5173

🎉 **Happy Chatting!**
