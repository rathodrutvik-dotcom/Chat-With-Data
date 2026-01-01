import os
import yaml
import shutil
import datetime
import uuid
import pytz
import logging
import gradio as gr


from langchain_groq import ChatGroq

from langchain_core.documents import Document
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredExcelLoader,
    UnstructuredWordDocumentLoader,
)

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma



# ---------------------------------------
# CONFIG
# ---------------------------------------
IST = pytz.timezone("Asia/Kolkata")
LOG_FILE = f"{datetime.datetime.now(IST).strftime('%m_%d_%Y_%H_%M_%S')}.log"
LOG_PATH = os.path.join("..", "logs")
os.makedirs(LOG_PATH, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_PATH, LOG_FILE),
    format="[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ---------------------------------------
# Embedding Model
# ---------------------------------------
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
)


# ---------------------------------------
# Helpers: Loaders
# ---------------------------------------
def load_docs(files):
    """Auto-detect loader based on file extension and load documents."""
    logging.info("Loading documents")

    loaders = {
        ".pdf": PyPDFLoader,
        ".xlsx": UnstructuredExcelLoader,
        ".docx": UnstructuredWordDocumentLoader,
    }

    docs = []
    for file in files:
        ext = os.path.splitext(file)[1].lower()

        if ext not in loaders:
            raise gr.Error(f"❌ Unsupported file extension: {ext}")

        try:
            loader = loaders[ext](file)
            loaded_docs = loader.load()
            docs.extend(loaded_docs)
            logging.info(f"Loaded {len(loaded_docs)} pages/sheets from {file}")
        except Exception as e:
            logging.error(f"Error loading {file}: {str(e)}")
            raise gr.Error(f"❌ Error loading {os.path.basename(file)}: {str(e)}")

    return docs


# ---------------------------------------
# Text Splitter
# ---------------------------------------
def get_document_chunks(docs):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    logging.info(f"Split into {len(splits)} chunks")
    return splits


# ---------------------------------------
# Vector Store (Chroma)
# ---------------------------------------
def get_vector_store(splits):
    """Create or update the vector store with a fixed collection name."""
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embedding_model,
        persist_directory="../chat_with_data",
        collection_name="chat_documents",  # Fixed collection name
    )
    logging.info("Vectorstore created/updated")
    return vectorstore


def get_retriever(vs):
    return vs.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 7, "fetch_k": 20},
    )


# ---------------------------------------
# System Prompt
# ---------------------------------------
def read_system_prompt(file_name):
    """Read system prompt from YAML file."""
    with open(f"./system_prompt/{file_name}", "r") as f:
        content = f.read().strip()
        return content


# ---------------------------------------
# RAG Chain (Modern LCEL)
# ---------------------------------------
def format_docs(docs):
    """Format retrieved documents into a single string."""
    return "\n\n".join(doc.page_content for doc in docs)


def build_rag_chain(system_prompt, retriever):
    """Build RAG chain with retriever and LLM."""
    logging.info("Building modern RAG pipeline")

    llm = ChatGroq(model="llama-3.3-70b-versatile")

    template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "Context:\n{context}\n\nQuestion: {question}"),
        ]
    )

    rag_chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough(),
        }
        | template
        | llm
        | StrOutputParser()
    )

    return rag_chain


# ---------------------------------------
# File Save
# ---------------------------------------
def create_unique_filename():
    """Generate a unique filename with timestamp."""
    uid = uuid.uuid4()
    timestamp = datetime.datetime.now(IST).strftime("%d-%m-%Y-%H-%M-%S")
    return f"file-{uid}-{timestamp}"


def validate_and_save_files(uploaded_files):
    """Validate and save uploaded files to the data directory."""
    if not uploaded_files:
        raise gr.Error("⚠️ Please upload at least one file.")

    file_group_name = create_unique_filename()
    saved_files = []

    for idx, file in enumerate(uploaded_files, start=1):
        ext = os.path.splitext(file.name)[1].lower()

        if ext not in [".pdf", ".docx", ".xlsx"]:
            raise gr.Error(f"❌ Unsupported file type: {ext}. Only PDF, DOCX, XLSX are allowed.")

        save_path = os.path.join("../data", f"{file_group_name}-{idx}{ext}")
        
        try:
            shutil.copyfile(file.name, save_path)
            saved_files.append(save_path)
            logging.info(f"Saved {file.name} → {save_path}")
        except Exception as e:
            logging.error(f"Error saving file {file.name}: {str(e)}")
            raise gr.Error(f"❌ Error saving file: {str(e)}")

    return saved_files, file_group_name


# ---------------------------------------
# MAIN RAG PROCESSOR
# ---------------------------------------
def proceed_input(text, uploaded_files):
    """Main function to process text and uploaded files into a RAG chain."""
    saved_files = []
    try:
        # Validate and save uploaded files
        saved_files, _ = validate_and_save_files(uploaded_files)

        # Load documents from files
        docs = load_docs(saved_files)
        logging.info(f"Loaded {len(docs)} documents from files")

        # Add user free text as document if provided
        if text and text.strip():
            docs.append(Document(page_content=text))
            logging.info("Added user text to documents")

        if not docs:
            raise gr.Error("❌ No content to process. Please upload files or enter text.")

        # Process documents
        splits = get_document_chunks(docs)
        vectorstore = get_vector_store(splits)
        retriever = get_retriever(vectorstore)
        system_prompt = read_system_prompt("custom.yaml")

        # Clean up uploaded files after processing
        for file_path in saved_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logging.info(f"Cleaned up: {file_path}")
            except Exception as e:
                logging.warning(f"Could not delete {file_path}: {e}")

        logging.info("RAG chain built successfully")
        return build_rag_chain(system_prompt, retriever)
    
    except gr.Error:
        raise
    except Exception as e:
        # Clean up files even if there's an error
        for file_path in saved_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
        logging.error(f"Error in proceed_input: {str(e)}")
        raise gr.Error(f"❌ Error processing documents: {str(e)}")


# ---------------------------------------
# ANSWER PROCESSING
# ---------------------------------------
def process_user_question(user_input, rag_chain):
    """Process user question and get answer from RAG chain."""
    try:
        # Ensure user_input is a string
        if isinstance(user_input, list):
            user_input = " ".join(str(item) for item in user_input)
        elif not isinstance(user_input, str):
            user_input = str(user_input)
        
        # Validate input
        if not user_input or not user_input.strip():
            return "Please enter a valid question."
        
        logging.info(f"User Q: {user_input}")
        answer = rag_chain.invoke(user_input)
        logging.info(f"Answer generated successfully: {len(answer)} chars")
        return answer
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error processing question: {error_msg}", exc_info=True)
        
        # Provide more specific error messages
        if "replace" in error_msg:
            return "Error: Document formatting issue. Please reprocess your documents."
        elif "API" in error_msg or "Groq" in error_msg:
            return "Error: API connection issue. Please check your GROQ_API_KEY."
        else:
            return f"Error: {error_msg}"
