import logging
import os

import gradio as gr
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredExcelLoader,
    UnstructuredWordDocumentLoader,
)


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
            logging.info("Loaded %s pages/sheets from %s", len(loaded_docs), file)
        except Exception as exc:  # pylint: disable=broad-except
            logging.error("Error loading %s: %s", file, str(exc))
            raise gr.Error(f"❌ Error loading {os.path.basename(file)}: {str(exc)}") from exc

    return docs


__all__ = ["load_docs"]
