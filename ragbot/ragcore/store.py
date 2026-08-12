"""The FAISS vector index: building it, saving it, loading it, searching it.

Two files make up a saved index and they must stay in step: ``index.faiss``
holds the vectors, ``chunks.json`` holds the passages in the same order. Row *i*
of the index is chunk *i* of the JSON — that is the whole contract.
"""

from __future__ import annotations

import json
from typing import List, Optional, Sequence

from .chunking import Chunk
from .config import Settings, get_settings
from .embeddings import Embedder, get_embedder
from .exceptions import IndexNotBuiltError


class SearchResult:
    """A retrieved chunk and how far it sat from the query."""

    __slots__ = ("chunk", "distance")

    def __init__(self, chunk: Chunk, distance: float) -> None:
        self.chunk = chunk
        self.distance = distance

    @property
    def text(self) -> str:
        return self.chunk.text

    @property
    def source(self) -> str:
        return self.chunk.source

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"SearchResult(source={self.source!r}, distance={self.distance:.3f})"


class VectorStore:
    """An in-memory FAISS index plus the chunks its rows correspond to."""

    def __init__(self, index, chunks: Sequence[Chunk]) -> None:
        self._index = index
        self.chunks: List[Chunk] = list(chunks)

    def __len__(self) -> int:
        return len(self.chunks)

    @classmethod
    def build(cls, chunks: Sequence[Chunk], embedder: Optional[Embedder] = None) -> "VectorStore":
        """Embed every chunk and load the vectors into a fresh flat L2 index."""
        import faiss

        chunks = list(chunks)
        embedder = embedder or get_embedder()
        vectors = embedder.encode([chunk.text for chunk in chunks])
        index = faiss.IndexFlatL2(vectors.shape[1])
        index.add(vectors)
        return cls(index, chunks)

    @classmethod
    def load(cls, settings: Optional[Settings] = None) -> "VectorStore":
        """Read a previously built index off disk."""
        import faiss

        settings = settings or get_settings()
        if not settings.index_path.is_file() or not settings.chunks_path.is_file():
            raise IndexNotBuiltError(
                f"No index at {settings.index_dir}. Build one with: python -m ragcore build-index"
            )

        index = faiss.read_index(str(settings.index_path))
        payload = json.loads(settings.chunks_path.read_text(encoding="utf-8"))
        chunks = [Chunk.from_dict(item) for item in payload]

        if index.ntotal != len(chunks):
            raise IndexNotBuiltError(
                f"Index holds {index.ntotal} vectors but chunks.json holds {len(chunks)} "
                "passages. Rebuild with: python -m ragcore build-index"
            )
        return cls(index, chunks)

    def save(self, settings: Optional[Settings] = None) -> None:
        """Write both halves of the index, creating the directory if needed."""
        import faiss

        settings = settings or get_settings()
        settings.index_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(settings.index_path))
        settings.chunks_path.write_text(
            json.dumps([chunk.to_dict() for chunk in self.chunks], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def search(self, query: str, k: int, embedder: Optional[Embedder] = None) -> List[SearchResult]:
        """Return the ``k`` nearest chunks to ``query``, closest first."""
        if not self.chunks:
            return []

        embedder = embedder or get_embedder()
        vector = embedder.encode_query(query)
        distances, indices = self._index.search(vector, max(1, min(k, len(self.chunks))))

        # FAISS pads with -1 when it finds fewer neighbours than asked for.
        return [
            SearchResult(self.chunks[position], float(distance))
            for distance, position in zip(distances[0], indices[0])
            if position != -1
        ]
