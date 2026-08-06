"""Retrieve, then generate — the two halves joined together.

Nothing here loads at import time. The index and the embedding model are pulled
in on first use and then held for the life of the process, which keeps Django
management commands and the test suite fast while still letting the web server
answer the second request without reloading anything.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from .config import Settings, get_settings
from .embeddings import get_embedder
from .generator import generate_answer
from .store import SearchResult, VectorStore


class RagPipeline:
    """Answers questions against one index."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._store: Optional[VectorStore] = None

    @property
    def store(self) -> VectorStore:
        """The index, loaded on first access."""
        if self._store is None:
            self._store = VectorStore.load(self.settings)
        return self._store

    def retrieve(self, question: str, k: Optional[int] = None) -> List[SearchResult]:
        """The passages most similar to ``question``."""
        return self.store.search(question, k or self.settings.top_k)

    def answer(self, question: str, k: Optional[int] = None) -> str:
        """Retrieve context for ``question`` and have Claude answer from it."""
        return generate_answer(question, self.retrieve(question, k), self.settings)

    def warmup(self) -> None:
        """Load the index and the embedding model now rather than mid-request."""
        _ = get_embedder().model  # touching it is what triggers the load
        _ = self.store


@lru_cache(maxsize=1)
def get_pipeline() -> RagPipeline:
    """The process-wide pipeline (call ``.cache_clear()`` in tests)."""
    return RagPipeline()


def answer_question(question: str, k: Optional[int] = None) -> str:
    """Convenience entry point used by the web app and the CLI."""
    return get_pipeline().answer(question, k)


def warmup() -> None:
    """Pay the model and index loading cost up front."""
    get_pipeline().warmup()
