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
from .generator import Answer, condense_question, generate_answer
from .history import get_history, recent_messages, record_turn
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

    def answer(
        self,
        question: str,
        k: Optional[int] = None,
        conversation_id: Optional[str] = None,
    ) -> Answer:
        """Retrieve context for ``question`` and have Claude answer from it.

        Given a ``conversation_id`` the earlier turns are loaded, the follow-up
        is rewritten into a standalone question *for retrieval only*, and the
        exchange is recorded once answered. Without one the turn is stateless,
        exactly as before.
        """
        store = get_history(conversation_id, self.settings) if conversation_id else None
        history = recent_messages(store, self.settings) if store is not None else []

        results = self.retrieve(condense_question(question, history, self.settings), k)
        answer = generate_answer(question, results, history, self.settings)

        if store is not None:
            record_turn(store, question, answer.text)
        return answer

    def warmup(self) -> None:
        """Load the index and the embedding model now rather than mid-request."""
        _ = get_embedder().model  # touching it is what triggers the load
        _ = self.store


@lru_cache(maxsize=1)
def get_pipeline() -> RagPipeline:
    """The process-wide pipeline (call ``.cache_clear()`` in tests)."""
    return RagPipeline()


def answer_question(
    question: str,
    k: Optional[int] = None,
    conversation_id: Optional[str] = None,
) -> Answer:
    """Convenience entry point used by the web app and the CLI."""
    return get_pipeline().answer(question, k, conversation_id)


def warmup() -> None:
    """Pay the model and index loading cost up front."""
    get_pipeline().warmup()
