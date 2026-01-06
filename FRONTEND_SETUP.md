# Chat with Documents - Complete Setup Guide

This guide covers setting up both the **Gradio backend** (existing) and the new **React frontend** with FastAPI backend.

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Backend Setup](#backend-setup)
3. [Frontend Setup](#frontend-setup)
4. [Running the Application](#running-the-application)
5. [API Documentation](#api-documentation)
6. [Troubleshooting](#troubleshooting)

## 🏗️ Architecture Overview

The application now has three components:

1. **Gradio App** (`src/main.py`) - Original interface (still working)
2. **FastAPI Backend** (`src/api_server.py`) - REST API for React frontend
3. **React Frontend** (`frontend/`) - Modern ChatGPT-like UI

```
┌─────────────────┐
│  React Frontend │  (Port 5173)
│   (Vite Dev)    │
└────────┬────────┘
         │
         │ HTTP REST API
         ▼
┌─────────────────┐
│ FastAPI Server  │  (Port 8000)
│  (api_server)   │
└────────┬────────┘
         │
         │ Uses existing code
         ▼
┌─────────────────┐
│   RAG Pipeline  │
│ Session Manager │
│  Vector Store   │
└─────────────────┘

┌─────────────────┐
│   Gradio App    │  (Port 7000) - Still working independently
└─────────────────┘
```

## 🔧 Backend Setup

### 1. Environment Setup

```bash
# Navigate to project root
cd /home/codevally/Documents/Projects/Chat-With-Data

# Create/activate virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows
```

### 2. Install Dependencies

```bash
# Install existing requirements
pip install -r requirements.txt

# Install additional dependencies for FastAPI
pip install fastapi uvicorn python-multipart
```

Update your `requirements.txt` to include:
```
# Add these lines at the end
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6
```

### 3. Environment Variables

Create/update `.env` file in project root:

```env
# API Keys
GROQ_API_KEY=your_groq_api_key_here

# Server Configuration (optional)
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
GRADIO_HOST=0.0.0.0
GRADIO_PORT=7000
```

### 4. Database Setup

The SQLite database is created automatically when you first run the application. No manual setup needed.

## 🎨 Frontend Setup

### 1. Navigate to Frontend Directory

```bash
cd frontend
```

### 2. Install Node Dependencies

```bash
npm install
```

This will install all required packages including:
- React 18
- Vite
- Tailwind CSS
- Axios
- React Icons
- React Markdown
- And more...

### 3. Configure API URL (Optional)

Create `.env` file in `frontend/` directory:

```env
VITE_API_URL=http://localhost:8000/api
```

If not set, it defaults to `http://localhost:8000/api`.

## 🚀 Running the Application

### Option 1: Run Everything Together

#### Terminal 1 - FastAPI Backend
```bash
# From project root
cd src
python api_server.py
```

API will be available at: `http://localhost:8000`
API docs at: `http://localhost:8000/docs`

#### Terminal 2 - React Frontend
```bash
# From project root
cd frontend
npm run dev
```

Frontend will be available at: `http://localhost:5173`

#### Terminal 3 - Gradio App (Optional)
```bash
# From project root
cd src
python main.py
```

Gradio will be available at: `http://localhost:7000`

### Option 2: Production Build

#### Build Frontend
```bash
cd frontend
npm run build
```

#### Serve with a Web Server
```bash
# Using Python
cd frontend/dist
python -m http.server 3000

# Or using Node
npm install -g serve
serve -s dist -p 3000
```

## 📚 API Documentation

### FastAPI Interactive Docs

Once the FastAPI server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

#### Session Management
```
GET    /api/sessions              - List all sessions
GET    /api/sessions/{id}/info    - Get session details
GET    /api/sessions/{id}/messages - Get chat history
POST   /api/sessions/{id}/clear   - Clear chat history
DELETE /api/sessions/{id}         - Delete session
```

#### Document Upload
```
POST   /api/upload                - Upload and process documents
       Body: multipart/form-data with files
       Returns: session_id, document_name
```

#### Chat
```
POST   /api/chat                  - Send message
       Body: { "session_id": "...", "message": "..." }
       Returns: { "role": "assistant", "content": "..." }
```

#### Health Check
```
GET    /api/health                - Check server status
```

## 🎯 Usage Flow

### 1. Upload Documents

1. Click "New Chat" in sidebar
2. Click "Upload Documents" or drag & drop files
3. Select PDF, DOCX, or XLSX files
4. Click "Upload & Process"
5. Wait for processing (progress bar shown)

### 2. Start Chatting

1. Session automatically selected after upload
2. Type your question in the input box
3. Press Enter to send (Shift+Enter for new line)
4. AI response appears with typing indicator
5. All messages automatically saved

### 3. Manage Sessions

- **Switch Sessions**: Click any session in sidebar
- **Delete Session**: Hover over session, click trash icon
- **View Details**: Session shows message count and last updated time

## 🐛 Troubleshooting

### Backend Issues

#### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill the process or change port in api_server.py
```

#### Import Errors
```bash
# Ensure you're in the correct directory
cd src
python api_server.py

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/Chat-With-Data/src"
```

#### API Key Issues
```bash
# Check .env file exists and has valid key
cat .env | grep GROQ_API_KEY

# Or set environment variable directly
export GROQ_API_KEY="your_key_here"
```

### Frontend Issues

#### Build Errors
```bash
# Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
```

#### API Connection Failed
1. Check FastAPI server is running (`http://localhost:8000/health`)
2. Check CORS settings in `api_server.py`
3. Verify API URL in `.env` file
4. Open browser console for detailed errors

#### Styling Issues
```bash
# Rebuild Tailwind
cd frontend
npm run build
```

### Common Issues

#### Session Not Found
- **Cause**: Backend restarted, sessions are in-memory
- **Solution**: Reupload documents or restart with persistent storage

#### Slow Response
- **Cause**: Large documents or many queries
- **Solution**: Check backend logs, increase timeouts

#### Upload Fails
- **Cause**: File too large or unsupported format
- **Solution**: Check file size/format, view backend logs

## 🔒 Security Notes

### Production Deployment

1. **Environment Variables**: Never commit `.env` files
2. **API Keys**: Use secrets management in production
3. **CORS**: Restrict allowed origins in `api_server.py`
4. **File Upload**: Add file size limits and validation
5. **Rate Limiting**: Add rate limiting for API endpoints

### Example Production CORS
```python
# In api_server.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific domain
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
```

## 📊 Performance Optimization

### Backend
- Use async endpoints for better concurrency
- Implement caching for frequently accessed data
- Add connection pooling for database

### Frontend
- Enable code splitting in Vite
- Lazy load components
- Implement virtual scrolling for long message lists
- Add service worker for offline support

## 🧪 Testing

### Backend Testing
```bash
# Install pytest
pip install pytest pytest-asyncio httpx

# Run tests (if you create them)
pytest tests/
```

### Frontend Testing
```bash
cd frontend

# Install testing libraries
npm install -D @testing-library/react @testing-library/jest-dom vitest

# Run tests
npm run test
```

## 🚢 Deployment Options

### Backend
- **Docker**: Containerize the FastAPI app
- **Cloud**: Deploy to AWS, GCP, Azure
- **VPS**: Ubuntu server with Nginx reverse proxy

### Frontend
- **Vercel**: `vercel deploy`
- **Netlify**: `netlify deploy`
- **GitHub Pages**: Build and deploy static files
- **S3 + CloudFront**: AWS static hosting

## 📞 Support

For issues:
1. Check this documentation
2. Review logs in `src/logs/`
3. Check browser console for frontend issues
4. Review FastAPI logs for backend issues

## 🎉 Next Steps

1. **Customize**: Modify colors and branding
2. **Enhance**: Add more features (export chat, share sessions)
3. **Deploy**: Move to production environment
4. **Monitor**: Add logging and analytics
5. **Scale**: Implement load balancing if needed

---

**Enjoy your modern document chat application! 🚀**
