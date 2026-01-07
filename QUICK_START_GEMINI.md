# Quick Start Guide - Gemini Integration

## ✅ Installation Complete!

The Chat-With-Data application now supports both **Groq** and **Google Gemini** LLM providers.

## 🚀 Quick Setup

### Step 1: Configure Your `.env` File

Choose one of the following configurations:

#### Option A: Use Groq (Default)
```bash
GROQ_API_KEY=your_groq_api_key_here
USE_GROQ=true
USE_GEMINI=false
```

#### Option B: Use Gemini 2.0 Flash
```bash
GEMINI_API_KEY=your_gemini_api_key_here
USE_GROQ=false
USE_GEMINI=true
```

#### Option C: Use Both (Gemini Priority with Groq Fallback)
```bash
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
USE_GROQ=true
USE_GEMINI=true
```

### Step 2: Get Your API Keys

- **Groq API Key**: https://console.groq.com
- **Gemini API Key**: https://makersuite.google.com/app/apikey

### Step 3: Run the Application

```bash
# Activate virtual environment
source venv/bin/activate

# Run Gradio interface
cd src
python main.py

# OR run FastAPI backend
python api_server.py
```

## 🎯 Configuration Options

### Boolean Flags
- `USE_GROQ`: Enable/disable Groq (default: `true`)
- `USE_GEMINI`: Enable/disable Gemini (default: `false`)

### Model Selection
- `GROQ_MODEL`: Groq model name (default: `llama-3.1-8b-instant`)
- `GEMINI_MODEL`: Gemini model name (default: `gemini-2.0-flash-exp`)

### Available Groq Models
- `llama-3.1-8b-instant` (default, fast)
- `llama-3.3-70b-versatile` (more capable)
- `mixtral-8x7b-32768` (good balance)

### Available Gemini Models
- `gemini-2.0-flash-exp` (default, latest experimental)
- `gemini-1.5-flash` (stable, fast)
- `gemini-1.5-pro` (most capable)

## 🔄 Switching Between Providers

Simply update your `.env` file and restart the application:

```bash
# Switch to Gemini
USE_GROQ=false
USE_GEMINI=true

# Switch to Groq
USE_GROQ=true
USE_GEMINI=false
```

## 🛡️ Priority Logic

When both providers are enabled:
1. **Gemini** is tried first
2. If Gemini fails, **Groq** is used as fallback
3. If both fail or both are disabled, an error is shown

## 📝 Example `.env` File

```bash
# API Keys
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxx

# LLM Provider Configuration
USE_GROQ=true
USE_GEMINI=true

# Model Selection (optional)
GROQ_MODEL=llama-3.1-8b-instant
GEMINI_MODEL=gemini-2.0-flash-exp

# Server Configuration (optional)
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
GRADIO_HOST=0.0.0.0
GRADIO_PORT=7000
```

## ✨ What Changed?

### New Features
✅ Dual LLM provider support (Groq + Gemini)
✅ Boolean flags for easy provider switching
✅ Automatic fallback mechanism
✅ Custom model selection
✅ Enhanced error handling
✅ Backward compatible with existing Groq setup

### Modified Files
- `requirements.txt` - Added `langchain-google-genai`
- `src/config/settings.py` - Added LLM configuration
- `src/rag/pipeline.py` - Enhanced with dual provider support
- `src/main.py` - Load Gemini API key
- `src/api_server.py` - Load Gemini API key
- `.env.example` - Updated with new options
- `start.sh` - Updated .env template
- `README.md` - Updated documentation

### No Breaking Changes
- All existing Groq functionality preserved
- Default behavior unchanged (Groq enabled by default)
- Existing `.env` files continue to work

## 🧪 Testing

Test your setup:

```bash
# Activate venv
source venv/bin/activate

# Test Gemini import
python -c "from langchain_google_genai import ChatGoogleGenerativeAI; print('✅ Gemini ready')"

# Test Groq import
python -c "from langchain_groq import ChatGroq; print('✅ Groq ready')"
```

## 📚 Additional Documentation

- Full implementation details: `GEMINI_INTEGRATION.md`
- Main README: `README.md`
- Environment template: `.env.example`

## 🆘 Troubleshooting

### Error: "No LLM provider enabled"
- Set at least one of `USE_GROQ` or `USE_GEMINI` to `true`

### Error: "Please check your GEMINI_API_KEY"
- Verify your Gemini API key is correct
- Check you have API quota available

### Error: "Please check your GROQ_API_KEY"
- Verify your Groq API key is correct
- Check you have API quota available

### Websockets conflict
- Already fixed! The correct version is installed.

## 🎉 You're Ready!

Your application now supports both Groq and Gemini. Start the app and enjoy the flexibility of choosing your preferred LLM provider!
