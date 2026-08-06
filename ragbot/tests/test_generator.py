"""The prompt is the contract with the model, so pin its shape down."""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from ragcore.chunking import Chunk
from ragcore.generator import answer_text, build_prompt, generate_answer
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


class AnswerTextTests(TestCase):
    """LangChain returns either a string or a list of content blocks."""

    def test_plain_string_content(self):
        self.assertEqual(answer_text(SimpleNamespace(content="Bengaluru.")), "Bengaluru.")

    def test_skips_a_leading_thinking_block(self):
        # Adaptive thinking is on by default, so this shape arrives whenever
        # the model decides to think — the answer is not the first block.
        message = SimpleNamespace(
            content=[
                {"type": "thinking", "thinking": "", "signature": "abc"},
                {"type": "text", "text": "Bengaluru."},
            ]
        )

        self.assertEqual(answer_text(message), "Bengaluru.")

    def test_joins_multiple_text_blocks(self):
        message = SimpleNamespace(
            content=[
                {"type": "text", "text": "Bengaluru, "},
                {"type": "text", "text": "India."},
            ]
        )

        self.assertEqual(answer_text(message), "Bengaluru, India.")

    def test_tolerates_bare_strings_in_the_block_list(self):
        self.assertEqual(answer_text(SimpleNamespace(content=["a", "b"])), "ab")


class GenerateAnswerTests(TestCase):
    settings = SimpleNamespace(chat_model="claude-sonnet-5", max_tokens=1024)

    def test_sends_the_prompt_to_the_model_and_returns_its_text(self):
        model = MagicMock()
        model.invoke.return_value = SimpleNamespace(content="Bengaluru.")

        with patch("ragcore.generator.build_model", return_value=model) as build:
            answer = generate_answer("where?", [result("alpha")], self.settings)

        self.assertEqual(answer, "Bengaluru.")
        build.assert_called_once_with(self.settings)

        prompt = model.invoke.call_args[0][0]
        self.assertIn("where?", prompt)
        self.assertIn("alpha", prompt)
