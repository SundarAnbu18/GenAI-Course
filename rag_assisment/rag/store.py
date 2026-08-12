"""Tasks 2-3 — embed the chunks and retrieve the nearest ones."""

from functools import lru_cache

from langchain_core.vectorstores import InMemoryVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

from .config import EMBED_MODEL, TOP_K
from .ingest import load_chunks


@lru_cache(maxsize=1)
def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )


def build_store(chunks=None):
    chunks = load_chunks() if chunks is None else chunks
    return InMemoryVectorStore.from_documents(chunks, get_embeddings())


def search(store, question, k=TOP_K):
    """Top-k chunks with their similarity scores — Task 3."""
    return store.similarity_search_with_score(question, k=k)