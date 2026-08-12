"""Errors the RAG pipeline raises, so callers can tell them apart.

The Django views map these onto HTTP status codes, and the CLI turns them into
readable messages instead of tracebacks.
"""


class RagError(Exception):
    """Base class for every error raised by this package."""


class ConfigurationError(RagError):
    """Something required is missing from the environment (e.g. the API key)."""


class IndexNotBuiltError(RagError):
    """The FAISS index has not been built yet — run `python -m ragcore build-index`."""


class NoDocumentsError(RagError):
    """The documents directory is empty or contains no readable text."""
