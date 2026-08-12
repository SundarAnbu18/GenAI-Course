"""Turning retrieved chunks into an answer with Claude, through LangChain.

Grounding the model in the retrieved context is what makes this retrieval
augmented rather than just a chatbot: without that instruction the model fills
gaps from memory and the sources stop meaning anything.

Two model calls happen per turn once a conversation is under way. The first
rewrites a follow-up into a standalone question so retrieval has something
searchable; the second answers it. See ``condense_question`` for why.

``ChatAnthropic`` wraps the official Anthropic SDK, so the model and the
request are the same as a direct call. What LangChain buys is the runnable
interface and the message types — the chat model can be swapped, bound, or
composed into a chain without the rest of the package noticing.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional, Sequence

from .config import Settings, get_settings
from .store import SearchResult

SYSTEM_TEMPLATE = """You are answering questions about the documents excerpted below.

Answer from the context when the question is about the documents. You may also
refer to the conversation so far when the user asks about it. If the answer is in
neither, say you don't know — never answer from outside knowledge.

Context:
{context}"""

CONDENSE_TEMPLATE = """Given the conversation so far and a follow-up message, rewrite the follow-up as a standalone question that makes sense without the conversation. If it is already standalone, return it unchanged. Return only the question.

Conversation:
{history}

Follow-up: {question}"""


@dataclass(frozen=True)
class Answer:
    """An answer, plus the metadata about how it was produced."""

    text: str
    model: str
    temperature: Optional[float]
    input_tokens: int
    output_tokens: int
    stop_reason: Optional[str]
    sources: List[SearchResult]

    def to_dict(self) -> dict:
        """The JSON payload the API returns."""
        return {
            "answer": self.text,
            "model": self.model,
            "temperature": self.temperature,
            "usage": {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
            },
            "stop_reason": self.stop_reason,
            "sources": [
                {
                    "source": result.source,
                    "distance": round(result.distance, 3),
                    "preview": result.text[:120],
                }
                for result in self.sources
            ],
        }


def build_system_prompt(results: Sequence[SearchResult]) -> str:
    """Lay the retrieved passages out as context for the model."""
    context = "\n".join(result.text for result in results)
    return SYSTEM_TEMPLATE.format(context=context)


def build_model(settings: Optional[Settings] = None):
    """Construct a LangChain chat model for these settings."""
    # Imported here so that `import ragcore` stays fast and side-effect free.
    from langchain_anthropic import ChatAnthropic

    settings = settings or get_settings()

    options = {}
    # Only send temperature when configured — current models reject a
    # non-default value with a 400.
    if settings.temperature is not None:
        options["temperature"] = settings.temperature

    return ChatAnthropic(
        model=settings.chat_model,
        max_tokens=settings.max_tokens,
        api_key=settings.require_api_key(),
        **options,
    )


@lru_cache(maxsize=1)
def get_model():
    """The process-wide chat model (call ``.cache_clear()`` in tests)."""
    return build_model()


def _model_for(settings: Settings):
    """The cached model in the normal case; a fresh one for explicit settings."""
    return get_model() if settings is get_settings() else build_model(settings)


def answer_text(message) -> str:
    """Pull the text out of a LangChain message.

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


def transcript(history: Sequence) -> str:
    """Render prior turns as plain text, for the condensing prompt."""
    speaker = {"human": "User", "ai": "Assistant"}
    return "\n".join(
        f"{speaker.get(message.type, message.type)}: {answer_text(message)}"
        for message in history
    )


def condense_question(
    question: str,
    history: Optional[Sequence] = None,
    settings: Optional[Settings] = None,
) -> str:
    """Rewrite a follow-up so it stands on its own.

    Only retrieval uses this — the model still answers the question in the
    user's own words. Without it "and his cloud skills?" gets embedded as that
    fragment and retrieves nothing useful, which is how multi-turn RAG usually
    falls apart.
    """
    if not history:
        return question

    settings = settings or get_settings()
    message = _model_for(settings).invoke(
        CONDENSE_TEMPLATE.format(history=transcript(history), question=question)
    )
    # A blank rewrite is worse than no rewrite.
    return answer_text(message).strip() or question


def generate_answer(
    question: str,
    results: Sequence[SearchResult],
    history: Optional[Sequence] = None,
    settings: Optional[Settings] = None,
) -> Answer:
    """Ask Claude the question, grounded in ``results`` and the prior turns."""
    from langchain_core.messages import HumanMessage, SystemMessage

    settings = settings or get_settings()

    messages = [SystemMessage(content=build_system_prompt(results))]
    messages.extend(history or [])
    messages.append(HumanMessage(content=question))

    message = _model_for(settings).invoke(messages)

    # Both are absent on some responses and on hand-built test doubles.
    usage = getattr(message, "usage_metadata", None) or {}
    metadata = getattr(message, "response_metadata", None) or {}

    return Answer(
        text=answer_text(message),
        model=metadata.get("model_name", settings.chat_model),
        temperature=settings.temperature,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        stop_reason=metadata.get("stop_reason"),
        sources=list(results),
    )
