# Project Explanation

## Goal
- Enable document-driven question answering by combining uploaded PDFs, DOCX, and XLSX files with optional free-form text.
- Surface answers that cite context preserved in a vector store backed by Chroma and retrieved via LangChain.

## Architecture overview
- `src/main.py` launches a Gradio Blocks interface that accepts uploads and text, persists state between interactions, and routes requests through helper functions.
- `src/utils.py` validates and stores uploads, loads documents with format-specific loaders, splits text with `RecursiveCharacterTextSplitter`, embeds chunks with `sentence-transformers/all-MiniLM-L6-v2`, and constructs a LangChain pipeline with Groq LLaMA 3.3 70B.
- `system_prompt/custom.yaml` supplies the fixed system instructions that keep responses contextual, concise, and transparent.

## Data flow
1. User uploads files or pastes text and clicks "Process Documents".
2. Files are saved under `data/` with UUID+timestamp names, then loaded, chunked, and embedded.
3. Chroma stores embeddings in `embedding_store/chat_documents`; retrieval uses MMR (`k=7`, `fetch_k=20`).
4. The retriever is combined with the system prompt and Groq LLM via `ChatPromptTemplate` to form the RAG chain.
5. Each chat question feeds into `process_user_question`, which invokes the chain and returns the generated answer with error handling for formatting or API issues.

## Operational details
- Run `pip install -r requirements.txt`, set `GROQ_API_KEY` (and optional `NGROK_AUTH_TOKEN`) in `.env`, then `python src/main.py`.
- Logs are written to `logs/` with IST timestamps; flake8 reports can be generated with `./generate_flake8_reports.sh`.
- Uploaded documents persist in `data/`, while embeddings persist in `embedding_store/` so reprocessing is not required until new files are added.

## Key dependencies
- Gradio for the UI and session state handling.
- LangChain components for loaders, splitters, retrievers, and prompts.
- `langchain_groq.ChatGroq` for calling the Groq LLM.
- HuggingFace sentence transformers for CPU-based embeddings.
- Chroma for vector persistence and MMR retrieval.
