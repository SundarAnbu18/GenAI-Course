# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

Three independent parts, no shared code between them:

- `ragbot/` — the deployed RAG chatbot: FAISS + sentence-transformers retrieval, Claude generation, Django web layer.
- `personal_rag/` — a single-file teaching RAG over a notes folder. Deliberately *not* the same system as `ragbot`: TF-IDF (upgrading to MiniLM when installed), no FAISS, no web layer.
- `course/` — Python exercises and solutions, one directory per module.
- `docs/deployment.md` — the production runbook (GCP VM, systemd, gunicorn, nginx, Netlify-embedded widget).

## Commands

The virtualenv currently in use is at the **repo root** (`.venv/`, Python 3.9), not inside `ragbot/` as the READMEs suggest. Run everything for ragbot from the `ragbot/` directory — `ragcore`, `ragweb` and `chatbot` are top-level packages there, which is what keeps imports free of path juggling.

```bash
cd ragbot && source ../.venv/bin/activate
```

```bash
python manage.py test                          # 87 tests, ~2.5s
python manage.py test tests.test_views         # one module
python manage.py test tests.test_views.AskApiTests.test_returns_the_answer
python manage.py runserver                     # http://127.0.0.1:8000
python -m ragcore build-index                  # rebuild after editing data/documents/
python -m ragcore search "cloud"               # retrieval only — no API call, no cost
python -m ragcore ask "who is sundar?"
python -m ragcore chat
```

`search` is the debugging tool: it prints exactly which passages were retrieved and their distances, which separates a retrieval problem from a generation problem.

personal_rag has no build step — its index rebuilds whenever a note changes:

```bash
cd personal_rag && python personal_rag.py chat
```

There is no linter or formatter configured, and no pytest — the suite runs on Django's own runner.

## ragbot architecture

The split that matters: **`ragcore` contains no Django imports anywhere**, and `chatbot` knows nothing about embeddings. The web layer validates input, calls `answer_question()` and maps `RagError` subclasses onto status codes. Keep it that way — the CLI and the tests reach the same engine.

Flow through `ragcore`: `indexing` reads `data/documents/*.{txt,md}` → `chunking` splits on blank lines (one paragraph = one chunk) → `embeddings` (MiniLM) → `store` writes the FAISS index. At query time `pipeline` retrieves top-k and `generator` calls Claude via `langchain_anthropic.ChatAnthropic`.

Invariants and conventions worth knowing before editing:

- **Index contract**: `var/index/index.faiss` row *i* corresponds to `chunks.json` entry *i*. `VectorStore.load()` refuses to load them out of step. Both files are gitignored and rebuildable.
- **Nothing loads at import time.** `faiss`, `sentence_transformers` and `langchain_anthropic` are imported inside functions; the embedding model, index and chat model are `lru_cache`d singletons. This is what keeps `import ragcore` and the test suite fast. Preserve the lazy imports when adding code.
- **All configuration goes through `ragcore/config.py`.** No other module touches `os.environ`. `get_settings()` is `lru_cache`d — call `get_settings.cache_clear()` in tests (and `get_pipeline.cache_clear()`, `get_model.cache_clear()`, `get_embedder.cache_clear()` where relevant).
- **`RAG_TEMPERATURE` is only sent when explicitly set.** `claude-sonnet-5`, `claude-opus-5`, `claude-opus-4-8` and `claude-fable-5` reject the parameter with a 400. Default is `None`, and `Answer.temperature` is `null` in the API response.
- **Two model calls per turn once a conversation exists**: `condense_question()` rewrites the follow-up into a standalone question *for retrieval only*, then `generate_answer()` answers the user's original wording with prior turns in context.
- **Conversation history**: `RAG_HISTORY_DSN` empty means an in-process dict, which is correct for `runserver` and silently wrong under gunicorn's multiple workers. Conversation ids are validated as UUIDs before becoming keys in a shared store.
- **The system prompt instructs the model to answer only from retrieved context or the conversation, and otherwise say it doesn't know.** That grounding is what makes this RAG rather than a chatbot; don't loosen it casually.
- **No database.** `DATABASES = {}` — no models, no sessions, no admin. Tests use `SimpleTestCase`.
- `/api/ask/` is `csrf_exempt` because it is called cross-origin; it is protected by the `X-Api-Key` header (constant-time compared) plus the CORS allowlist instead. The chat page POST is same-origin and CSRF-protected, so it needs no key.
- `/api/health/` deliberately does not load the index, so it stays cheap to poll.

Tests mock `chatbot.views.answer_question`, the Anthropic call and the embedder — nothing in the suite downloads a model or spends money. Keep it that way.

## personal_rag architecture

The idea it exists to demonstrate: **PROFILE** (a constant in the file) is sent on every single call and never retrieved, because it is relevant to every question and similarity search could only drop it; **NOTES** are retrieved per question because the pile grows unbounded. Metadata filtering by `--since`/`--tag` happens *before* ranking — "what did I work on in June" is a date question, not a meaning question.

`pick_embedder()` returns the MiniLM embedder when `sentence-transformers` is importable and falls back to the hand-written TF-IDF one, so the script runs with only numpy. `.rag_index.npz` is a cache keyed by a fingerprint of the note paths and embedder name; it rebuilds itself when either changes.

## Conventions

- Secrets live in `.env` (gitignored). `ragbot/.env.example` lists every variable the chatbot understands, with notes on the ones that bite. `ragcore/config.py` and `personal_rag.py` each parse `.env` by hand — anything already in the environment wins over the file, so systemd and the shell can always override.
- Generated files — `ragbot/var/`, `personal_rag/.rag_index.npz`, `staticfiles/`, `*.sqlite3` — are gitignored and never committed.
- The codebase is heavily commented in a specific voice: module docstrings explain *why* a design choice was made, not what the code does. Match that when adding modules.

## Known cruft

- `ragbot/ragcore/histort.py` is a stray fragment (typo'd filename, undefined names, imported by nothing). `history.py` is the real module.
- `ragbot/README.md` claims 45 tests; there are 87.
- The READMEs tell you to create `ragbot/.venv`; the working one is at the repo root.
