from dataclasses import dataclass

from langchain_chroma import Chroma


@dataclass
class RagSession:
    rag_chain: object
    vectorstore: Chroma
    sparse_index: "SparseIndex"


__all__ = ["RagSession"]
