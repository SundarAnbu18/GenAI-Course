# GenAI-Course

Course work and the two RAG systems built alongside it.

```
GenAI-Course/
├── ragbot/         production RAG chatbot — FAISS + Claude + Django   (deployed)
├── personal_rag/   single-file personal RAG over a notes folder       (teaching version)
├── course/         Python exercises and solutions
└── docs/           deployment runbook
```

## ragbot

The deployed one. Retrieval runs locally over a FAISS index of
sentence-transformer embeddings; Claude writes the answer from the retrieved
passages only. Django serves a chat page plus a JSON API that an embedded
widget calls from another site.

```bash
cd ragbot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # add your ANTHROPIC_API_KEY
python -m ragcore build-index
python manage.py runserver
```

[Full documentation](ragbot/README.md) · [deployment runbook](docs/deployment.md)

## personal_rag

The same idea stripped to one readable file: TF-IDF retrieval (upgrading itself
to MiniLM when available), a fixed profile sent on every call, and notes
filtered by date and tag before ranking. No web layer, no FAISS.

```bash
cd personal_rag && python personal_rag.py chat
```

[Full documentation](personal_rag/README.md)

## course

Python fundamentals — [exercises and solutions](course/README.md) by module.

## Conventions

- Secrets live in `.env`, which is gitignored. `ragbot/.env.example` lists
  every variable the chatbot understands.
- Generated files — vector indexes, caches, `staticfiles/` — are gitignored and
  rebuildable. Nothing generated is committed.
- Run `ragbot` commands from the `ragbot/` directory; that's where its packages
  are importable from.
