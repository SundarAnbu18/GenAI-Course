# personal_rag

A single-file personal RAG, written to be read end to end. It answers questions
about Sundar from a folder of notes, with a fixed profile that rides along on
every call.

This is deliberately *not* the same system as [`ragbot`](../ragbot). It is the
teaching version: no FAISS, no web layer, and a TF-IDF fallback so it still runs
with nothing but numpy installed.

```bash
cd personal_rag
python personal_rag.py chat
python personal_rag.py ask "how should I introduce myself to a new client?"
python personal_rag.py sources               # what's currently indexed
python personal_rag.py ask "..." --since 2026-06-01 --tag client
```

`ANTHROPIC_API_KEY` is read from `personal_rag/.env` or the repo-root `.env`.

## How it differs from ragbot

| | personal_rag | ragbot |
| --- | --- | --- |
| Retrieval | TF-IDF, or MiniLM if installed | MiniLM + FAISS |
| Corpus | `notes/` with front-matter metadata | `data/documents/` |
| Filtering | by date and tag, before ranking | none |
| Interface | CLI | CLI + web + JSON API |
| Index | `.rag_index.npz`, rebuilt when notes change | built explicitly |

The metadata filtering is the idea worth stealing: "what did I work on in June"
is a date question, not a meaning question, so it filters first and ranks second.

## Notes

`notes/` is the corpus — plain `.md` or `.txt`, optionally with front matter:

```
---
date: 2026-07-28
tags: client-acme, scoping
---
```

The index rebuilds itself whenever a note changes, so there is no build step.
