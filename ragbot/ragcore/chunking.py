"""Turning source documents into the units that get embedded and retrieved.

One paragraph — text between blank lines — is one chunk. Paragraphs in these
documents are already self-contained statements, so they retrieve far more
precisely than fixed-size windows, which tend to cut sentences in half.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Chunk:
    """A retrievable passage, and the file it came from."""

    text: str
    source: str

    def to_dict(self) -> dict:
        return {"text": self.text, "source": self.source}

    @classmethod
    def from_dict(cls, data: dict) -> "Chunk":
        return cls(text=data["text"], source=data.get("source", ""))


def split_paragraphs(text: str) -> List[str]:
    """Split on blank lines and collapse the whitespace inside each paragraph."""
    return [" ".join(part.split()) for part in text.split("\n\n") if part.strip()]


def chunk_document(text: str, source: str) -> List[Chunk]:
    """Chunk one document, tagging every chunk with its filename."""
    return [Chunk(text=body, source=source) for body in split_paragraphs(text)]
