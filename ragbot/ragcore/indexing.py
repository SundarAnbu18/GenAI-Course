"""Reading the corpus off disk and turning it into a saved index.

This is the offline half of the system: run it whenever the documents change,
and the web app picks up the result on its next restart.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .chunking import Chunk, chunk_document
from .config import Settings, get_settings
from .exceptions import NoDocumentsError
from .store import VectorStore

DOCUMENT_SUFFIXES = (".txt", ".md")


def iter_document_paths(documents_dir: Path) -> List[Path]:
    """Every indexable file under ``documents_dir``, in a stable order."""
    if not documents_dir.is_dir():
        return []
    return sorted(
        path
        for path in documents_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in DOCUMENT_SUFFIXES
    )


def load_chunks(settings: Optional[Settings] = None) -> List[Chunk]:
    """Read and chunk the whole corpus."""
    settings = settings or get_settings()
    paths = iter_document_paths(settings.documents_dir)
    if not paths:
        raise NoDocumentsError(
            f"No {' or '.join(DOCUMENT_SUFFIXES)} files found in {settings.documents_dir}"
        )

    chunks: List[Chunk] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        chunks.extend(chunk_document(text, source=path.name))

    if not chunks:
        raise NoDocumentsError(f"{settings.documents_dir} contains no readable text")
    return chunks


def build_index(settings: Optional[Settings] = None) -> VectorStore:
    """Chunk, embed and persist the corpus. Returns the store it just wrote."""
    settings = settings or get_settings()
    chunks = load_chunks(settings)
    store = VectorStore.build(chunks)
    store.save(settings)
    return store
