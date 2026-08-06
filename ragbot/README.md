# ragbot

A retrieval-augmented chatbot. Retrieval runs locally — sentence-transformer
embeddings in a FAISS index — and only the answer generation goes to Claude.
Django serves a chat page and a JSON API that an embedded widget calls from
another site.

## Layout

```
ragbot/
├── manage.py               Django entry point
├── ragcore/                the RAG engine — no Django imports anywhere in here
│   ├── config.py           every tunable, read from the environment
│   ├── chunking.py         documents -> retrievable passages
│   ├── embeddings.py       the sentence-transformer, loaded lazily
│   ├── store.py            the FAISS index: build, save, load, search
│   ├── indexing.py         the offline job that writes the index
│   ├── generator.py        prompt construction + the Claude call
│   ├── pipeline.py         retrieve-then-generate, joined up
│   └── cli.py              python -m ragcore <command>
├── ragweb/                 Django project (settings, urls, wsgi, asgi)
├── chatbot/                Django app (views, urls, template, widget.js)
├── data/documents/         the corpus — drop .txt and .md files here
├── var/index/              generated index (gitignored, rebuildable)
└── tests/                  python manage.py test
```

The split that matters: `ragcore` knows nothing about HTTP, and `chatbot` knows
nothing about embeddings. The web layer validates input, calls
`answer_question()` and maps errors onto status codes.

## Quickstart

```bash
cd ragbot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then put your ANTHROPIC_API_KEY in it
python -m ragcore build-index
python manage.py runserver
```

Then open http://127.0.0.1:8000.

Run every command from this directory — `ragcore`, `ragweb` and `chatbot` are
top-level packages here, which is what keeps the imports free of path juggling.

## CLI

```bash
python -m ragcore build-index          # rebuild after editing data/documents/
python -m ragcore ask "who is sundar?" # one question, one answer
python -m ragcore search "cloud"       # retrieval only — no API call, no cost
python -m ragcore chat                 # interactive loop
```

`search` is the one to reach for when an answer looks wrong: it shows exactly
which passages were retrieved and how far each sat from the query, which
separates a retrieval problem from a generation problem.

## Configuration

Everything comes from the environment; `.env.example` lists the lot with
defaults. The ones worth knowing:

| Variable | Default | What it does |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | — | Required to generate answers |
| `RAG_TOP_K` | `3` | Passages retrieved per question |
| `RAG_CHAT_MODEL` | `claude-sonnet-5` | Model used for the answer |
| `RAG_EAGER_LOAD` | off | Load the model at boot, not on first request |
| `WIDGET_API_KEY` | empty | Shared secret for `/api/ask/`; empty disables the check |
| `CORS_ALLOWED_ORIGINS` | empty | Sites allowed to call the API from a browser |

## API

```
POST /api/ask/      {"question": "..."}  ->  {"answer": "..."}
GET  /api/health/   ->  {"status": "ok", "index_ready": true}
```

`/api/ask/` returns 400 for a malformed or over-long question, 401 when
`WIDGET_API_KEY` is set and the `X-Api-Key` header doesn't match, and 503 when
the index hasn't been built. `/api/health/` deliberately does not load the
index, so it stays cheap enough to poll.

## Embedding the widget

```html
<script>
  window.RAGBOT_CONFIG = {
    apiUrl: 'https://your-host/api/ask/',
    apiKey: 'your-widget-api-key'
  };
</script>
<script src="https://your-host/static/chatbot/widget.js"></script>
```

The host needs that site listed in `CORS_ALLOWED_ORIGINS`.

## Tests

```bash
python manage.py test
```

45 tests, well under a second — the embedding model and the Anthropic API are
mocked, so nothing here downloads a model or spends money.

## Deployment

See [../docs/deployment.md](../docs/deployment.md).
