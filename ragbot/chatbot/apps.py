"""App configuration, including the optional model warmup."""

from __future__ import annotations

import logging
import os

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ChatbotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chatbot"

    def ready(self) -> None:
        """Load the embedding model and index at boot when asked to.

        Worth it under gunicorn, where it moves a ~10s cost off the first user's
        request. Not worth it for management commands or tests, which is why it
        is opt-in rather than automatic — set RAG_EAGER_LOAD=1 in production.
        """
        if os.environ.get("RAG_EAGER_LOAD", "").strip().lower() not in {"1", "true", "yes", "on"}:
            return

        from ragcore import warmup

        try:
            warmup()
        except Exception:
            # A cold index should not stop the server from booting; the first
            # request will report the real problem.
            logger.exception("RAG warmup failed; continuing without it")
        else:
            logger.info("RAG warmup complete")
