#!/bin/bash

# Quick Start Script for Chat with Documents Application
# This script starts both FastAPI backend and React frontend

echo "🚀 Starting Chat with Documents Application..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Node.js installation
echo "Checking prerequisites..."
if ! command_exists node; then
    echo -e "${RED}❌ Error: Node.js is not installed!${NC}"
    echo -e "${YELLOW}Please install Node.js from: https://nodejs.org/${NC}"
    echo -e "${YELLOW}Or use: sudo apt install nodejs npm (Ubuntu/Debian)${NC}"
    exit 1
fi

NODE_VERSION=$(node -v)
echo -e "${GREEN}✅ Node.js installed: $NODE_VERSION${NC}"

if ! command_exists npm; then
    echo -e "${RED}❌ Error: npm is not installed!${NC}"
    exit 1
fi

NPM_VERSION=$(npm -v)
echo -e "${GREEN}✅ npm installed: $NPM_VERSION${NC}"

# Check Python installation
if ! command_exists python3; then
    echo -e "${RED}❌ Error: Python 3 is not installed!${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✅ $PYTHON_VERSION${NC}"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found!${NC}"
    echo "Creating .env file template..."
    cat > .env << EOF
# API Keys
GROQ_API_KEY=your_groq_api_key_here

# Server Configuration
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
GRADIO_HOST=0.0.0.0
GRADIO_PORT=7000
EOF
    echo -e "${GREEN}✅ Created .env file. Please add your GROQ_API_KEY!${NC}"
    echo ""
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check Python dependencies
echo "Checking Python dependencies..."
pip install -q -r requirements.txt fastapi uvicorn python-multipart

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}⚠️  Frontend dependencies not found. Installing...${NC}"
    echo "This may take a few minutes on first run..."
    cd frontend
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to install frontend dependencies${NC}"
        exit 1
    fi
    cd ..
    echo -e "${GREEN}✅ Frontend dependencies installed${NC}"
else
    echo -e "${GREEN}✅ Frontend dependencies already installed${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Starting Servers...${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping servers...${NC}"
    kill $FASTAPI_PID $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}✅ Servers stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start FastAPI backend
echo -e "${BLUE}📡 Starting FastAPI Backend on http://localhost:8000${NC}"
cd src
python api_server.py &
FASTAPI_PID=$!
cd ..

# Wait a bit for backend to start
echo "Waiting for backend to initialize..."
sleep 5

# Check if backend is running
if ! kill -0 $FASTAPI_PID 2>/dev/null; then
    echo -e "${RED}❌ Backend failed to start! Check logs in src/logs/${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Backend is ready${NC}"

# Start React frontend
echo -e "${BLUE}🎨 Starting React Frontend on http://localhost:5173${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   ✅ Application Started!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "📱 ${BLUE}React Frontend:${NC}   http://localhost:5173"
echo -e "🔌 ${BLUE}FastAPI Backend:${NC}  http://localhost:8000"
echo -e "📚 ${BLUE}API Documentation:${NC} http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all servers${NC}"
echo ""

# Wait for processes
wait $FASTAPI_PID $FRONTEND_PID
