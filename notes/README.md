---
tags: meta
---
This folder is the retrieval corpus for my_rag.py. Anything here is searchable.

Add notes as plain .md or .txt files. Optional front matter at the top of a
file gives the retriever metadata to filter on:

---
date: 2026-07-28
tags: client-acme, scoping
---

Then: python my_rag.py ask "what did we decide about auth?" --tag client-acme

Good things to keep here: meeting notes, client context, architecture
decisions and why they were made, snippets you re-explain often, drafts of
things you write repeatedly. The index rebuilds itself when files change.
