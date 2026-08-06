"""Command line access to the pipeline: ``python -m ragcore <command>``.

    python -m ragcore build-index          # after editing data/documents/
    python -m ragcore ask "who is sundar?"
    python -m ragcore search "cloud skills" # retrieval only, no API call
    python -m ragcore chat
"""

from __future__ import annotations

import argparse
import sys
import uuid
from typing import List, Optional

from .config import get_settings
from .exceptions import RagError
from .indexing import build_index
from .pipeline import get_pipeline


def _cmd_build_index(args: argparse.Namespace) -> int:
    settings = get_settings()
    print(f"Reading documents from {settings.documents_dir}")
    store = build_index(settings)
    print(f"Indexed {len(store)} chunks -> {settings.index_path}")
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    answer = get_pipeline().answer(" ".join(args.question), args.top_k)
    print(answer.text)

    meta = [answer.model]
    if answer.temperature is not None:
        meta.append(f"temp {answer.temperature}")
    meta.append(f"{answer.input_tokens} in / {answer.output_tokens} out")
    print(f"\n[{' · '.join(meta)}]")
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    results = get_pipeline().retrieve(" ".join(args.question), args.top_k)
    if not results:
        print("No matches.")
        return 0
    for result in results:
        preview = result.text[:90].strip()
        print(f"  {result.distance:.3f}  {result.source:<16} {preview}...")
    return 0


def _cmd_chat(args: argparse.Namespace) -> int:
    pipeline = get_pipeline()
    # One id for the session, so follow-ups can refer back to earlier answers.
    conversation_id = str(uuid.uuid4())
    print("Ask about the indexed documents. Ctrl-C or 'exit' to quit.\n")
    while True:
        try:
            question = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if question.lower() in {"exit", "quit", ""}:
            return 0
        print("\n" + pipeline.answer(question, args.top_k, conversation_id).text + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m ragcore", description=__doc__.splitlines()[0])
    parser.add_argument("-k", "--top-k", type=int, default=None, help="how many chunks to retrieve")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("build-index", help="rebuild the index from data/documents/").set_defaults(
        handler=_cmd_build_index
    )

    ask = subparsers.add_parser("ask", help="answer a single question")
    ask.add_argument("question", nargs="+")
    ask.set_defaults(handler=_cmd_ask)

    search = subparsers.add_parser("search", help="show retrieved chunks without calling the API")
    search.add_argument("question", nargs="+")
    search.set_defaults(handler=_cmd_search)

    subparsers.add_parser("chat", help="interactive question loop").set_defaults(handler=_cmd_chat)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except RagError as exc:
        # Expected failures (no API key, no index) read better without a traceback.
        print(f"error: {exc}", file=sys.stderr)
        return 1
