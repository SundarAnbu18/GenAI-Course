"""Chunk size/overlap, model IDs, paths, and API-key loading."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 180

EMBED_MODEL = "all-MiniLM-L6-v2"
LLM_MODEL = "claude-haiku-4-5"
TOP_K = 3


def load_env():
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())