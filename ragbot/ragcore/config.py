"""Every tunable knob in one place, read from the environment.

The rest of the package never touches ``os.environ`` directly — it asks for
``get_settings()``. That keeps the defaults visible in a single file and makes
the pipeline configurable in production without editing code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .exceptions import ConfigurationError

# ragbot/ragcore/config.py -> ragbot/
PROJECT_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = PROJECT_DIR.parent


def load_env_file(path: Path) -> None:
    """Load ``KEY=VALUE`` pairs from a .env file into ``os.environ``.

    Values already present in the environment win, so systemd or the shell can
    always override the file. Written by hand to avoid a python-dotenv
    dependency for twelve lines of parsing.
    """
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def load_dotenv() -> None:
    """Pick up ragbot/.env, falling back to the .env at the repo root."""
    load_env_file(PROJECT_DIR / ".env")
    load_env_file(REPO_DIR / ".env")


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    return Path(raw).expanduser().resolve() if raw else default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer, got {raw!r}") from exc


@dataclass(frozen=True)
class Settings:
    """Resolved configuration for one process."""

    documents_dir: Path
    index_dir: Path
    embedding_model: str
    chat_model: str
    top_k: int
    max_tokens: int
    anthropic_api_key: str

    @property
    def index_path(self) -> Path:
        """The FAISS index itself."""
        return self.index_dir / "index.faiss"

    @property
    def chunks_path(self) -> Path:
        """The chunk texts, in the same order as the vectors in the index."""
        return self.index_dir / "chunks.json"

    def require_api_key(self) -> str:
        if not self.anthropic_api_key:
            raise ConfigurationError(
                "ANTHROPIC_API_KEY is not set. Put it in ragbot/.env or export it."
            )
        return self.anthropic_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build the settings once per process (call ``get_settings.cache_clear()`` in tests)."""
    load_dotenv()
    return Settings(
        documents_dir=_env_path("RAG_DOCUMENTS_DIR", PROJECT_DIR / "data" / "documents"),
        # Generated files live under var/ so they stay out of version control.
        index_dir=_env_path("RAG_INDEX_DIR", PROJECT_DIR / "var" / "index"),
        embedding_model=os.environ.get("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        chat_model=os.environ.get("RAG_CHAT_MODEL", "claude-sonnet-5"),
        top_k=_env_int("RAG_TOP_K", 3),
        max_tokens=_env_int("RAG_MAX_TOKENS", 1024),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    )
