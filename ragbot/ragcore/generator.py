"""Turning retrieved chunks into an answer with Claude, through LangChain.

The instruction to answer only from the context is what makes this retrieval
augmented rather than just a chatbot: without it the model happily fills gaps
from memory, and the citations stop meaning anything.

``ChatAnthropic`` wraps the official Anthropic SDK, so the model and the
request are the same as a direct call. What LangChain buys is the runnable
interface — the chat model can be swapped, bound, or composed into a chain
without the rest of the package noticing.
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


def build_model(settings: Optional[Settings] = None):
    """Construct a LangChain chat model for these settings."""
    # Imported here so that `import ragcore` stays fast and side-effect free.
    from langchain_anthropic import ChatAnthropic  # from langchain_anthropic we are importing ChatAnthropic

    settings = settings or get_settings()
    return ChatAnthropic(
        model=settings.chat_model,
        max_tokens=settings.max_tokens,
        api_key=settings.require_api_key(),
    )


@lru_cache(maxsize=1)
def get_model():
    """The process-wide chat model (call ``.cache_clear()`` in tests)."""
    return build_model()


def answer_text(message) -> str:
    """Pull the answer out of a LangChain message.

    ``content`` is a plain string most of the time, but becomes a list of
    blocks whenever the model thinks — so never assume either shape.
    """
    content = message.content
    if isinstance(content, str):
        return content

    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


def generate_answer(
    question: str,
    results: Sequence[SearchResult],
    settings: Optional[Settings] = None,
) -> str:
    """Ask Claude the question, grounded in ``results``."""
    settings = settings or get_settings()
    # Reuse the cached model in the normal case; honour an explicit override.
    model = get_model() if settings is get_settings() else build_model(settings)
    return answer_text(model.invoke(build_prompt(question, results)))
