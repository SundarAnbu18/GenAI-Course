"""A small retrieval-augmented generation library.

Retrieval runs locally over a FAISS index of sentence-transformer embeddings;
generation goes to Claude. Nothing in here knows about Django, so the same code
backs the web app, the CLI and the tests.

    from ragcore import answer_question
    answer_question("what does sundar work on?")

The web layer lives in ``chatbot`` and ``ragweb``; this package is the engine.
"""

from .chunking import Chunk, chunk_document, split_paragraphs
from .config import Settings, get_settings
from .exceptions import (
    ConfigurationError,
    IndexNotBuiltError,
    NoDocumentsError,
    RagError,
)
from .indexing import build_index, load_chunks
from .pipeline import RagPipeline, answer_question, get_pipeline, warmup
from .store import SearchResult, VectorStore

__all__ = [
    "Chunk",
    "ConfigurationError",
    "IndexNotBuiltError",
    "NoDocumentsError",
    "RagError",
    "RagPipeline",
    "SearchResult",
    "Settings",
    "VectorStore",
    "answer_question",
    "build_index",
    "chunk_document",
    "get_pipeline",
    "get_settings",
    "load_chunks",
    "split_paragraphs",
    "warmup",
]
