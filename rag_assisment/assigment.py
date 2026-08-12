"""Entry point — search / ask / evaluate.

Imports are absolute (`from rag.chain import ...`), not relative: this file is
run as a script, not imported as part of a package, so `from .config import ...`
would raise "attempted relative import with no known parent package".
"""

import argparse
from pathlib import Path

from rag.chain import answer
from rag.config import TOP_K
from rag.store import build_store, search


def cmd_search(args):
    """Retrieval only — no API call, no cost. Use this to debug retrieval."""
    store = build_store()
    for doc, score in search(store, args.question, k=args.k):
        source = Path(doc.metadata["source"]).name
        print(f"\n[{score:.3f}] {source} p{doc.metadata.get('page')}")
        print(doc.page_content[:300])


def cmd_ask(args):
    store = build_store()
    result = answer(store, args.question, k=args.k, grounded=not args.ungrounded)
    print(result["answer"])
    used = {Path(doc.metadata["source"]).name for doc in result["context"]}
    print("\nretrieved from:", ", ".join(sorted(used)))


def cmd_evaluate(args):
    from evaluation.questions import QUESTIONS

    store = build_store()
    for question in QUESTIONS:
        result = answer(store, question["question"])
        print(f"\n[{question['kind']}] {question['question']}")
        print(f"  expected: {question['expected']}")
        print(f"  got:      {result['answer']}")


def main():
    parser = argparse.ArgumentParser(description="RAG over the assignment corpus")
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("search", help="retrieval only — no API call, no cost")
    p.add_argument("question")
    p.add_argument("-k", type=int, default=TOP_K)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("ask", help="full pipeline")
    p.add_argument("question")
    p.add_argument("-k", type=int, default=TOP_K)
    p.add_argument("--ungrounded", action="store_true",
                   help="drop the answer-only-from-context rules (Task 4)")
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("evaluate", help="run the 10 evaluation questions")
    p.set_defaults(func=cmd_evaluate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
