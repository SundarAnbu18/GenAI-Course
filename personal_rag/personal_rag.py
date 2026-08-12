"""
personal_rag.py — a personal RAG for Sundar Anbu, calling the Anthropic API.

    pip install numpy anthropic          # sentence-transformers optional, see below

    # Put the key in .env (loaded automatically), or export it:
    #   ANTHROPIC_API_KEY=sk-ant-...
    #   export ANTHROPIC_API_KEY=sk-ant-...

    python personal_rag.py ask "how should I introduce myself to a new client?"
    python personal_rag.py chat
    python personal_rag.py sources             # what's currently indexed
    python personal_rag.py ask "..." --since 2026-06-01 --tag client

ARCHITECTURE — the part worth understanding
    Two different kinds of "about me" go to Claude, and they are handled
    differently on purpose.

    PROFILE   Always sent, every single call, never retrieved. Who you are,
              what you do, how you write. This is relevant to every question,
              so putting it through similarity search would only create a way
              for it to get accidentally left out.

    NOTES     Retrieved per question. The growing pile — meeting notes, client
              context, decisions, drafts, snippets. Only the relevant slice is
              sent, because the whole pile will eventually be far too large.

    Remember the API is stateless. Claude learns nothing between calls. Each
    request re-sends PROFILE plus whatever was retrieved, and the model reads
    it fresh every time. Your disk is the memory; Claude is only the reader.
"""

from __future__ import annotations

import glob
import hashlib
import json
import math
import os
import sys
import textwrap
from collections import Counter
from datetime import date

import numpy as np

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Paths hang off this file, not the shell's working directory, so the script
# works the same whether it is run from here or from the repo root.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

NOTES_DIR = os.path.join(BASE_DIR, "notes")        # drop .md / .txt files here, any structure
INDEX_PATH = os.path.join(BASE_DIR, ".rag_index.npz")  # cache; rebuilt when files change
# ANTHROPIC_API_KEY lives in one of these; never commit them
ENV_PATHS = (os.path.join(BASE_DIR, ".env"), os.path.join(os.path.dirname(BASE_DIR), ".env"))
CHAT_MODEL = "claude-sonnet-5"
CHUNK_WORDS = 220
CHUNK_OVERLAP = 40
TOP_K = 5
MIN_SCORE = 0.05                       # drop weak matches instead of padding the prompt
NEURAL_MODEL = "all-MiniLM-L6-v2"      # used automatically if installed; see pick_embedder


def load_env(paths: tuple[str, ...] = ENV_PATHS) -> None:
    """Load KEY=VALUE pairs from .env into os.environ (no python-dotenv needed)."""
    for path in paths:
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = value


load_env()


# ---------------------------------------------------------------------------
# PROFILE — always sent to Claude. Edit this freely; it is the highest-value
# part of the file.
#
# Seeded from sundaranbu.com. The site renders client-side, so only the
# server-visible content came through — fill in the [TODO] lines and this
# gets sharply better. Keep it under ~40 lines; it rides along on every call.
# ---------------------------------------------------------------------------

PROFILE = """
# Who I am
Name: Sundar Anbu
Role: Forward Deployed Engineer
Based in: Bengaluru, India (IST)
Site: https://sundaranbu.com   Twitter: @sundaranbu_

# What I do
I embed with customers to scope ambiguous problems, and ship production
software that moves real metrics. I work directly with clients to define
technical scope, then develop and deploy production-ready systems end to end.
4+ years of experience across healthcare, edtech, and AI startups.

# Stack
Languages: TypeScript, Python
Frontend: React
Backend: Node.js
Focus: AI workflows, full-stack delivery

# Current work                                                      [TODO]
Employer / clients:
What I am building right now:
Problems I own:

# How I like to work                                                [TODO]
Writing style (e.g. direct, no filler, short paragraphs):
Code preferences (e.g. single-file scripts, typed, minimal deps):
Things I never want suggested:

# Background                                                        [TODO]
Notable projects and what they actually achieved:
Education:
"""


# ---------------------------------------------------------------------------
# Seed notes — a starting corpus so the system works before you write anything.
# These become real files under ./notes on first run, so you can edit them like
# any other note rather than editing code.
# ---------------------------------------------------------------------------

SEED_NOTES: dict[str, str] = {
    "about-me.md": """---
tags: profile, bio
---
Sundar Anbu is a Forward Deployed Engineer based in Bengaluru. He embeds with
customers to scope ambiguous problems and ships production software that moves
real metrics.

He has 4+ years of experience spanning healthcare, edtech, and AI startups,
working directly with clients to define technical scope, then developing and
deploying production-ready systems end to end.

His stack is TypeScript and Python, React on the frontend, Node.js on the
backend, with a focus on AI workflows and full-stack delivery. He writes at
sundaranbu.com and posts as @sundaranbu_.
""",
    "how-i-work.md": """---
tags: profile, working-style
---
The forward deployed model: the engineer sits with the customer rather than
behind a ticket queue. Scope is ambiguous at the start, so the first job is
turning a vague business problem into a technical one that can be shipped.

What this means in practice: talk to the customer directly, define scope with
them rather than for them, build the smallest thing that moves the metric they
care about, deploy it to production, and measure whether it moved.
""",
    "README.md": """---
tags: meta
---
This folder is the retrieval corpus for personal_rag.py. Anything here is searchable.

Add notes as plain .md or .txt files. Optional front matter at the top of a
file gives the retriever metadata to filter on:

---
date: 2026-07-28
tags: client-acme, scoping
---

Then: python personal_rag.py ask "what did we decide about auth?" --tag client-acme

Good things to keep here: meeting notes, client context, architecture
decisions and why they were made, snippets you re-explain often, drafts of
things you write repeatedly. The index rebuilds itself when files change.
""",
}


# ---------------------------------------------------------------------------
# Loading notes, with front matter
# ---------------------------------------------------------------------------

def parse_front_matter(text: str) -> tuple[dict, str]:
    """Pull an optional leading '---' block off a note. No yaml dependency."""
    meta: dict = {}
    if not text.startswith("---"):
        return meta, text
    end = text.find("\n---", 3)
    if end == -1:
        return meta, text
    for line in text[3:end].strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip().lower()] = value.strip()
    return meta, text[end + 4:].lstrip()


def ensure_notes(folder: str = NOTES_DIR) -> None:
    """First run: create ./notes and write the seed files."""
    if os.path.isdir(folder) and glob.glob(os.path.join(folder, "**", "*.*"), recursive=True):
        return
    os.makedirs(folder, exist_ok=True)
    for name, body in SEED_NOTES.items():
        with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
            f.write(body)
    print(f"Created {folder}/ with {len(SEED_NOTES)} starter notes. Add your own anytime.")


def note_paths(folder: str = NOTES_DIR) -> list[str]:
    files = glob.glob(os.path.join(folder, "**", "*.*"), recursive=True)
    return sorted(p for p in files if p.lower().endswith((".md", ".txt")))


def load_notes(folder: str = NOTES_DIR) -> list[dict]:
    """Return one record per note: text plus the metadata used for filtering."""
    notes = []
    for path in note_paths(folder):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
        meta, body = parse_front_matter(raw)
        if not body.strip():
            continue
        notes.append({
            "text": body,
            "source": os.path.relpath(path, folder),
            # Fall back to the file's own modified date, so "--since" works
            # even on notes you never bothered to tag.
            "date": meta.get("date") or date.fromtimestamp(os.path.getmtime(path)).isoformat(),
            "tags": [t.strip().lower() for t in meta.get("tags", "").split(",") if t.strip()],
        })
    return notes


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, size: int = CHUNK_WORDS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    if not words:
        return []
    step = max(1, size - overlap)
    return [c for c in (" ".join(words[i:i + size]) for i in range(0, len(words), step)) if c.strip()]


def build_chunks(notes: list[dict]) -> list[dict]:
    return [
        {"text": piece, "source": n["source"], "date": n["date"], "tags": n["tags"]}
        for n in notes for piece in chunk_text(n["text"])
    ]


# ---------------------------------------------------------------------------
# Embeddings
#
# TF-IDF by default so this runs with nothing but numpy. If sentence-transformers
# is installed it is used automatically and retrieval gets meaningfully better —
# TF-IDF matches shared words, so "reimbursed" and "money back" look unrelated
# to it. Install when you want that fixed:  pip install sentence-transformers
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    return [w.strip(".,!?()[]\"'`:;").lower() for w in text.split()
            if w.strip(".,!?()[]\"'`:;")]


class TfidfEmbedder:
    name = "tfidf"

    def fit(self, texts: list[str]):
        docs = [tokenize(t) for t in texts]
        vocab = sorted({w for d in docs for w in d})
        self.index = {w: i for i, w in enumerate(vocab)}
        n = len(docs)
        df = Counter(w for d in docs for w in set(d))
        self.idf = np.array([math.log((1 + n) / (1 + df[w])) + 1.0 for w in vocab], dtype="float32")
        return self

    def encode(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), len(self.index)), dtype="float32")
        for row, text in enumerate(texts):
            counts = Counter(tokenize(text))
            total = sum(counts.values()) or 1
            for word, count in counts.items():
                col = self.index.get(word)
                if col is not None:
                    out[row, col] = (count / total) * self.idf[col]
        return normalize(out)


class NeuralEmbedder:
    name = "minilm"

    def __init__(self, model):
        self.model = model

    def fit(self, texts: list[str]):
        return self                       # nothing to learn from your corpus

    def encode(self, texts: list[str]) -> np.ndarray:
        return normalize(np.asarray(self.model.encode(texts), dtype="float32"))


def normalize(vecs: np.ndarray) -> np.ndarray:
    return vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-10)


def pick_embedder():
    """Prefer the neural model, but never let its absence break the tool.

    The model is loaded here rather than lazily, because the failure that
    matters is not a missing import — it is a missing download. First run on a
    plane, behind a proxy, or with a cold cache would otherwise crash mid-index.
    """
    try:
        from sentence_transformers import SentenceTransformer
        return NeuralEmbedder(SentenceTransformer(NEURAL_MODEL))
    except ImportError:
        return TfidfEmbedder()
    except Exception as exc:
        print(f"note: '{NEURAL_MODEL}' unavailable ({type(exc).__name__}); using tf-idf")
        return TfidfEmbedder()


# ---------------------------------------------------------------------------
# The index — built on demand, cached, rebuilt when your notes change
# ---------------------------------------------------------------------------

def fingerprint(paths: list[str], embedder_name: str) -> str:
    """Changes whenever a note is edited, added, removed, or settings change."""
    parts = [f"{p}:{os.path.getmtime(p)}:{os.path.getsize(p)}" for p in paths]
    parts.append(f"{CHUNK_WORDS}:{CHUNK_OVERLAP}:{embedder_name}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


class Index:
    def __init__(self, folder: str = NOTES_DIR, quiet: bool = False):
        ensure_notes(folder)
        self.embedder = pick_embedder()
        stamp = fingerprint(note_paths(folder), self.embedder.name)

        if os.path.exists(INDEX_PATH):
            cached = np.load(INDEX_PATH, allow_pickle=True)
            if str(cached["stamp"]) == stamp:
                self.chunks = json.loads(str(cached["chunks"]))
                self.vectors = cached["vectors"]
                self.embedder.fit([c["text"] for c in self.chunks])   # restore vocab
                return

        self.chunks = build_chunks(load_notes(folder))
        if not self.chunks:
            sys.exit(f"No notes found in {folder}/. Add a .md file and retry.")
        if not quiet:
            print(f"Indexing {len(self.chunks)} chunks with {self.embedder.name}...")
        self.embedder.fit([c["text"] for c in self.chunks])
        self.vectors = self.embedder.encode([c["text"] for c in self.chunks])
        np.savez(INDEX_PATH, vectors=self.vectors,
                 chunks=np.array(json.dumps(self.chunks)), stamp=np.array(stamp))

    def search(self, question: str, k: int = TOP_K,
               since: str | None = None, tag: str | None = None) -> list[dict]:
        """Filter on metadata FIRST, then rank what survives by similarity.

        This ordering matters. 'What did I work on in June' is a date question,
        not a meaning question — embeddings cannot answer it and never will.
        Filtering first is how real systems handle time and scope.
        """
        keep = [
            i for i, c in enumerate(self.chunks)
            if (since is None or c["date"] >= since)
            and (tag is None or tag.lower() in c["tags"])
        ]
        if not keep:
            return []

        q_vec = self.embedder.encode([question])[0]
        scores = self.vectors[keep] @ q_vec
        order = np.argsort(scores)[::-1][:k]
        hits = [{**self.chunks[keep[i]], "score": float(scores[i])} for i in order]
        return [h for h in hits if h["score"] >= MIN_SCORE]


# ---------------------------------------------------------------------------
# Prompt and generation
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = f"""You are Sundar's personal assistant. You have a fixed profile of
who he is, plus retrieved excerpts from his own notes.

<profile>
{PROFILE}
</profile>

Rules:
- The profile above is always true. Use it freely.
- For anything else, rely only on the retrieved notes provided in the message.
- Cite the note filename in brackets after claims drawn from notes, like [about-me.md].
- If the notes do not cover something, say so plainly rather than inventing it.
  Retrieval always returns its closest matches, even when nothing is relevant —
  so treat weak or off-topic excerpts as an absence of information.
- Write directly, in prose, without filler."""


def build_prompt(question: str, hits: list[dict]) -> str:
    if not hits:
        return (f"No notes matched this question.\n\nQuestion: {question}\n\n"
                f"Answer from the profile if possible, and say clearly that your "
                f"notes contain nothing on this.")
    blocks = "\n\n".join(
        f'<note source="{h["source"]}" date="{h["date"]}">\n{h["text"]}\n</note>'
        for h in hits
    )
    return f"<notes>\n{blocks}\n</notes>\n\nQuestion: {question}"


def generate(question: str, hits: list[dict]) -> str:
    import anthropic

    client = anthropic.Anthropic()          # reads ANTHROPIC_API_KEY
    response = client.messages.create(
        model=CHAT_MODEL,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_prompt(question, hits)}],
    )
    return response.content[0].text


def ask(question: str, index: Index, since=None, tag=None, show=True) -> str:
    hits = index.search(question, since=since, tag=tag)
    if show:
        if hits:
            print("\n  retrieved:")
            for h in hits:
                print(f"    {h['score']:.3f}  {h['source']:<18} {h['text'][:56].strip()}...")
        else:
            print("\n  retrieved: nothing above threshold — answering from profile only")
        print()
    return generate(question, hits)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def take_flag(args: list[str], name: str) -> str | None:
    if name in args:
        i = args.index(name)
        value = args[i + 1] if i + 1 < len(args) else None
        del args[i:i + 2]
        return value
    return None


def main() -> None:
    args = sys.argv[1:]
    since, tag = take_flag(args, "--since"), take_flag(args, "--tag")
    command = args[0] if args else "chat"

    if command == "sources":
        index = Index()
        print(f"embedder: {index.embedder.name}   chunks: {len(index.chunks)}\n")
        for source in sorted({c["source"] for c in index.chunks}):
            pieces = [c for c in index.chunks if c["source"] == source]
            tags = sorted({t for c in pieces for t in c["tags"]})
            print(f"  {source:<22} {len(pieces):>2} chunks  {pieces[0]['date']}"
                  f"  {', '.join(tags) if tags else '-'}")
        return

    if command == "reindex":
        if os.path.exists(INDEX_PATH):
            os.remove(INDEX_PATH)
        Index()
        print("Rebuilt.")
        return

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            "Set ANTHROPIC_API_KEY in .env, or:  export ANTHROPIC_API_KEY=sk-ant-..."
        )

    if command == "ask":
        if len(args) < 2:
            sys.exit('Usage: python personal_rag.py ask "your question" [--since DATE] [--tag TAG]')
        print(ask(" ".join(args[1:]), Index(), since, tag))

    elif command == "chat":
        index = Index()
        print("Ask about yourself, your notes, your work. Ctrl-C or 'exit' to quit.\n")
        while True:
            try:
                question = input("you > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if question.lower() in {"exit", "quit", ""}:
                return
            print("\n" + textwrap.fill(ask(question, index, since, tag), 100) + "\n")

    else:
        print(__doc__)


if __name__ == "__main__":
    main()