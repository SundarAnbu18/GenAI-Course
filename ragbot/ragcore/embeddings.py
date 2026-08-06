"""The sentence-transformer that turns text into vectors.

The model is a few hundred megabytes and takes seconds to load, so it is loaded
lazily and then cached for the life of the process. Importing this module is
cheap; the cost is paid on the first ``encode`` call.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Sequence

from .config import get_settings

if TYPE_CHECKING:  # pragma: no cover - import only for type checkers
    import numpy as np


class Embedder:
    """Wraps a SentenceTransformer and always hands back float32 for FAISS."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            # Imported here so that `import ragcore` stays fast and side-effect free.
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: Sequence[str]) -> "np.ndarray":
        """Embed a batch of texts as a (len(texts), dim) float32 array."""
        vectors = self.model.encode(list(texts), convert_to_numpy=True)
        return vectors.astype("float32")

    def encode_query(self, text: str) -> "np.ndarray":
        """Embed a single query, shaped (1, dim) the way FAISS expects."""
        return self.encode([text])


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    """Return the process-wide embedder (call ``.cache_clear()`` in tests)."""
    return Embedder(get_settings().embedding_model)
