"""Where a conversation lives between requests.

The Claude API is stateless — "memory" only ever means resending the earlier
turns. This module owns *where* those turns are kept: in process memory for
local runs, in a SQL store when ``RAG_HISTORY_DSN`` is set.

In production the DSN is not optional. gunicorn runs more than one worker, and
an in-process dict is only visible to whichever worker happened to serve the
request — so half the follow-ups would silently arrive with no history.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from .config import Settings, get_settings

# Conversation ids are minted by the browser and become keys in a shared store,
# so they are validated rather than trusted. A UUID passes; a path or an essay
# does not.
CONVERSATION_ID = re.compile(r"\A[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z")

# Only used when no DSN is configured; see the module docstring.
_MEMORY: Dict[str, object] = {}


def is_valid_conversation_id(value: str) -> bool:
    """True for a UUID-shaped id, which is all we ever hand out."""
    return bool(value) and bool(CONVERSATION_ID.match(value))


def get_history(conversation_id: str, settings: Optional[Settings] = None):
    """The message store for one conversation."""
    settings = settings or get_settings()

    if settings.history_dsn:
        from langchain_community.chat_message_histories import SQLChatMessageHistory

        return SQLChatMessageHistory(
            session_id=conversation_id, connection=settings.history_dsn
        )

    from langchain_core.chat_history import InMemoryChatMessageHistory

    if conversation_id not in _MEMORY:
        _MEMORY[conversation_id] = InMemoryChatMessageHistory()
    return _MEMORY[conversation_id]


def recent_messages(history, settings: Optional[Settings] = None) -> List:
    """The last few turns, oldest first.

    Bounding what we *read* is what protects the context window. The store
    itself keeps everything — how long to retain it is a retention policy, not
    a prompt concern.
    """
    settings = settings or get_settings()
    limit = max(settings.history_turns, 0) * 2
    if not limit:
        return []
    return list(history.messages)[-limit:]


def record_turn(history, question: str, answer: str) -> None:
    """Append one exchange to the store."""
    from langchain_core.messages import AIMessage, HumanMessage

    history.add_messages([HumanMessage(content=question), AIMessage(content=answer)])


def forget(conversation_id: str, settings: Optional[Settings] = None) -> None:
    """Drop a conversation entirely."""
    settings = settings or get_settings()
    if settings.history_dsn:
        get_history(conversation_id, settings).clear()
    else:
        _MEMORY.pop(conversation_id, None)
