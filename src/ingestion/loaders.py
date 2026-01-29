"""Handles document loading based on file types and enriches metadata."""

import os
import logging
import gradio as gr
from pathlib import Path
from typing import List, Optional
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredExcelLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredHTMLLoader,
)
from bs4 import BeautifulSoup


def get_short_source_name(filepath: str) -> str:
    """Get a short display name for the source document.

    Extracts just the filename without the collection prefix.
    e.g., 'doc_collection-1.pdf' -> 'document1.pdf' or original filename if available.
    """
    path = Path(filepath)
    return path.name


def extract_html_metadata(filepath: str) -> dict:
    """Extract metadata from HTML meta tags including display_name.
    
    Args:
        filepath: Path to HTML file
        
    Returns:
        Dictionary with metadata (url, domain, page_title, display_name)
    """
    metadata = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
            
            # Extract meta tags including new display_name
            for meta_name in ['source_url', 'domain', 'page_title', 'display_name']:
                meta_tag = soup.find('meta', attrs={'name': meta_name})
                if meta_tag and meta_tag.get('content'):
                    metadata[meta_name] = meta_tag['content']
    except Exception as e:
        logging.warning(f"Failed to extract HTML metadata from {filepath}: {str(e)}")
    
    return metadata


def load_docs(files: List[str], original_filenames: Optional[List[str]] = None) -> List[Document]:
    """Auto-detect loader based on file extension and load documents.

    Args:
        files: List of file paths to load
        original_filenames: Optional list of original filenames for source tracking

    Returns:
        List of loaded documents with source metadata
    """
    logging.info("Loading documents")

    loaders = {
        ".pdf": PyPDFLoader,
        ".xlsx": UnstructuredExcelLoader,
        ".docx": UnstructuredWordDocumentLoader,
        ".html": UnstructuredHTMLLoader,
    }

    docs = []
    for idx, file in enumerate(files):
        ext = os.path.splitext(file)[1].lower()
        if ext not in loaders:
            raise gr.Error(f"❌ Unsupported file extension: {ext}")

        # Determine the source name to use
        if original_filenames and idx < len(original_filenames):
            source_name = original_filenames[idx]
        else:
            source_name = get_short_source_name(file)

        try:
            loader = loaders[ext](file)
            loaded_docs = loader.load()

            # For HTML files, extract additional metadata from meta tags
            html_metadata = {}
            if ext == ".html":
                html_metadata = extract_html_metadata(file)

            # Enhance metadata with document source information
            for doc in loaded_docs:
                if doc.metadata is None:
                    doc.metadata = {}

                # Add original document filename for source tracking
                doc.metadata["document_name"] = source_name
                doc.metadata["document_path"] = file

                # For HTML files, add URL-specific metadata
                if html_metadata:
                    doc.metadata.update(html_metadata)
                    
                    # Use display_name (URL path) as the primary source identifier
                    if 'display_name' in html_metadata:
                        doc.metadata["source"] = html_metadata['display_name']
                        doc.metadata["display_source"] = html_metadata['display_name']
                    elif 'page_title' in html_metadata:
                        # Fallback to page title if display_name not available (backwards compatibility)
                        doc.metadata["source"] = html_metadata['page_title']
                        doc.metadata["display_source"] = html_metadata['page_title']
                    
                    # Store the actual URL for clickable citations
                    if 'source_url' in html_metadata:
                        doc.metadata["url"] = html_metadata['source_url']
                        doc.metadata["source_url"] = html_metadata['source_url']

                # Keep the source field but ensure it points to the readable name
                if "source" not in doc.metadata:
                    doc.metadata["source"] = source_name

            docs.extend(loaded_docs)
            logging.info(
                "Loaded %s pages/sheets from %s (source: %s)",
                len(loaded_docs), file, source_name
            )
        except Exception as exc:  # pylint: disable=broad-except
            logging.error("Error loading %s: %s", file, str(exc))
            raise gr.Error(f"❌ Error loading {os.path.basename(file)}: {str(exc)}") from exc

    return docs


__all__ = ["load_docs", "get_short_source_name", "extract_html_metadata"]
