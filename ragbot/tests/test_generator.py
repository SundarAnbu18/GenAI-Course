"""The prompt is the contract with the model, so pin its shape down."""

from unittest import TestCase

from ragcore.chunking import Chunk
from ragcore.generator import build_prompt
from ragcore.store import SearchResult


def result(text: str) -> SearchResult:
    return SearchResult(Chunk(text=text, source="document.txt"), distance=0.1)


class BuildPromptTests(TestCase):
    def test_includes_the_question_and_every_chunk(self):
        prompt = build_prompt("who?", [result("alpha"), result("beta")])

        self.assertIn("who?", prompt)
        self.assertIn("alpha", prompt)
        self.assertIn("beta", prompt)

    def test_instructs_the_model_to_stay_inside_the_context(self):
        prompt = build_prompt("who?", [result("alpha")])

        self.assertIn("using only the context below", prompt)
        self.assertIn("say you don't know", prompt)

    def test_survives_having_retrieved_nothing(self):
        prompt = build_prompt("who?", [])

        self.assertIn("who?", prompt)
