"""Thin Flask UI over the assignment RAG pipeline.

No retrieval or generation lives here — every ask goes through
`build_store` + `answer`, the same entry points as the CLI.
"""

from functools import lru_cache
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from rag.chain import answer
from rag.store import build_store

MAX_QUESTION_LEN = 2000

app = Flask(__name__)


@lru_cache(maxsize=1)
def get_store():
    """Build the in-memory index once; first request pays the load cost."""
    return build_store()


def _sources_from_docs(docs):
    """Unique source filenames in retrieval order."""
    seen = set()
    names = []
    for doc in docs:
        name = Path(doc.metadata["source"]).name
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/ask")
def api_ask():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="Request body must be JSON."), 400

    question = payload.get("question")
    if not isinstance(question, str) or not question.strip():
        return jsonify(error="Field 'question' is required."), 400

    question = question.strip()
    if len(question) > MAX_QUESTION_LEN:
        return jsonify(
            error=f"Question must be at most {MAX_QUESTION_LEN} characters."
        ), 400

    grounded = payload.get("grounded", True)
    if not isinstance(grounded, bool):
        return jsonify(error="Field 'grounded' must be a boolean."), 400

    try:
        result = answer(get_store(), question, grounded=grounded)
    except Exception as exc:  # noqa: BLE001 — surface a clean JSON 500
        return jsonify(error=f"RAG failed: {exc}"), 500

    return jsonify(
        answer=result["answer"],
        sources=_sources_from_docs(result["context"]),
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
