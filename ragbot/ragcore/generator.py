"""Turning retrieved chunks into an answer with Claude.

The instruction to answer only from the context is what makes this retrieval
augmented rather than just a chatbot: without it the model happily fills gaps
from memory, and the citations stop meaning anything.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional, Sequence

from .config import Settings, get_settings
from .store import SearchResult

PROMPT_TEMPLATE = """Answer the question using only the context below. If the answer isn't in the context, say you don't know.

Context:
{context}

Question: {question}"""


def build_prompt(question: str, results: Sequence[SearchResult]) -> str:
    """Lay the retrieved passages out as context for the model."""
    context = "\n".join(result.text for result in results)
    return PROMPT_TEMPLATE.format(context=context, question=question)


@lru_cache(maxsize=1)
def get_client():
    """The Anthropic client, created once and reused (``.cache_clear()`` in tests)."""
    from anthropic import Anthropic

    return Anthropic(api_key=get_settings().require_api_key())


def generate_answer(
    question: str,
    results: Sequence[SearchResult],
    settings: Optional[Settings] = None,
) -> str:
    """Ask Claude the question, grounded in ``results``."""
    settings = settings or get_settings()
    response = get_client().messages.create(
        model=settings.chat_model,
        max_tokens=settings.max_tokens,
        messages=[{"role": "user", "content": build_prompt(question, results)}],
    )
    return response.content[0].text
