"""The prompt is the contract with the model, so pin its shape down."""

import json
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ragcore.chunking import Chunk
from ragcore.generator import (
    Answer,
    answer_text,
    build_system_prompt,
    condense_question,
    generate_answer,
    transcript,
)
from ragcore.store import SearchResult


def result(text: str) -> SearchResult:
    return SearchResult(Chunk(text=text, source="document.txt"), distance=0.1)


def an_answer(**overrides) -> Answer:
    defaults = dict(
        text="Bengaluru.",
        model="claude-sonnet-5",
        temperature=None,
        input_tokens=12,
        output_tokens=3,
        stop_reason="end_turn",
        sources=[result("alpha")],
    )
    defaults.update(overrides)
    return Answer(**defaults)


SETTINGS = SimpleNamespace(chat_model="claude-sonnet-5", max_tokens=1024, temperature=None)


class BuildSystemPromptTests(TestCase):
    def test_includes_every_chunk(self):
        prompt = build_system_prompt([result("alpha"), result("beta")])

        self.assertIn("alpha", prompt)
        self.assertIn("beta", prompt)

    def test_allows_the_conversation_as_well_as_the_context(self):
        # The old "only the context" wording made follow-ups about the
        # conversation itself unanswerable.
        prompt = build_system_prompt([result("alpha")])

        self.assertIn("Answer from the context", prompt)
        self.assertIn("conversation so far", prompt)
        self.assertIn("say you don't know", prompt)

    def test_survives_having_retrieved_nothing(self):
        self.assertIn("Context:", build_system_prompt([]))


class AnswerTextTests(TestCase):
    """LangChain returns either a string or a list of content blocks."""

    def test_plain_string_content(self):
        self.assertEqual(answer_text(SimpleNamespace(content="Bengaluru.")), "Bengaluru.")

    def test_skips_a_leading_thinking_block(self):
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


class TranscriptTests(TestCase):
    def test_labels_each_speaker(self):
        rendered = transcript([HumanMessage(content="who?"), AIMessage(content="Sundar.")])

        self.assertEqual(rendered, "User: who?\nAssistant: Sundar.")


class AnswerPayloadTests(TestCase):
    """to_dict() is the API contract — the widget and the page both read it."""

    def test_carries_the_answer_usage_and_sources(self):
        payload = an_answer().to_dict()

        self.assertEqual(payload["answer"], "Bengaluru.")
        self.assertEqual(payload["model"], "claude-sonnet-5")
        self.assertIsNone(payload["temperature"])
        self.assertEqual(payload["usage"], {"input_tokens": 12, "output_tokens": 3})
        self.assertEqual(payload["stop_reason"], "end_turn")
        self.assertEqual(payload["sources"][0]["source"], "document.txt")
        self.assertIn("alpha", payload["sources"][0]["preview"])

    def test_is_json_serialisable(self):
        json.dumps(an_answer(temperature=0.2).to_dict())


class CondenseQuestionTests(TestCase):
    """Retrieval needs a standalone question; the answer keeps the user's words."""

    def condense(self, question, history, reply="standalone?"):
        self.model = MagicMock()
        self.model.invoke.return_value = SimpleNamespace(content=reply)
        with patch("ragcore.generator.build_model", return_value=self.model):
            return condense_question(question, history, SETTINGS)

    def test_first_turn_costs_no_extra_call(self):
        model = MagicMock()
        with patch("ragcore.generator.build_model", return_value=model):
            self.assertEqual(condense_question("who?", [], SETTINGS), "who?")
        model.invoke.assert_not_called()

    def test_rewrites_a_follow_up_using_the_history(self):
        history = [HumanMessage(content="who is sundar?"), AIMessage(content="An engineer.")]

        rewritten = self.condense(
            "and his cloud skills?", history, reply="What are Sundar's cloud skills?"
        )

        self.assertEqual(rewritten, "What are Sundar's cloud skills?")
        prompt = self.model.invoke.call_args[0][0]
        self.assertIn("who is sundar?", prompt)
        self.assertIn("and his cloud skills?", prompt)

    def test_a_blank_rewrite_falls_back_to_the_original(self):
        history = [HumanMessage(content="hi"), AIMessage(content="hello")]

        self.assertEqual(self.condense("and?", history, reply="   "), "and?")


class GenerateAnswerTests(TestCase):
    def generate(self, message, history=None, settings=None):
        self.model = MagicMock()
        self.model.invoke.return_value = message
        with patch("ragcore.generator.build_model", return_value=self.model):
            return generate_answer(
                "where?", [result("alpha")], history, settings or SETTINGS
            )

    def test_sends_the_prompt_and_returns_the_metadata(self):
        answer = self.generate(
            SimpleNamespace(
                content="Bengaluru.",
                usage_metadata={"input_tokens": 12, "output_tokens": 3},
                response_metadata={
                    "model_name": "claude-sonnet-5",
                    "stop_reason": "end_turn",
                },
            )
        )

        self.assertEqual(answer.text, "Bengaluru.")
        self.assertEqual(answer.model, "claude-sonnet-5")
        self.assertEqual(answer.input_tokens, 12)
        self.assertEqual(answer.output_tokens, 3)
        self.assertEqual(answer.stop_reason, "end_turn")
        self.assertEqual([s.source for s in answer.sources], ["document.txt"])

    def test_builds_system_history_question_in_that_order(self):
        history = [HumanMessage(content="who?"), AIMessage(content="Sundar.")]

        self.generate(SimpleNamespace(content="ok"), history)

        messages = self.model.invoke.call_args[0][0]
        self.assertIsInstance(messages[0], SystemMessage)
        self.assertIn("alpha", messages[0].content)
        self.assertEqual([m.content for m in messages[1:3]], ["who?", "Sundar."])
        self.assertIsInstance(messages[-1], HumanMessage)
        self.assertEqual(messages[-1].content, "where?")

    def test_without_history_it_is_just_system_and_question(self):
        self.generate(SimpleNamespace(content="ok"))

        messages = self.model.invoke.call_args[0][0]
        self.assertEqual(len(messages), 2)

    def test_a_response_without_metadata_does_not_crash(self):
        answer = self.generate(SimpleNamespace(content="Bengaluru."))

        self.assertEqual(answer.input_tokens, 0)
        self.assertEqual(answer.output_tokens, 0)
        self.assertIsNone(answer.stop_reason)
        self.assertEqual(answer.model, "claude-sonnet-5")

    def test_reports_the_configured_temperature(self):
        settings = SimpleNamespace(
            chat_model="claude-sonnet-4-5", max_tokens=1024, temperature=0.2
        )

        answer = self.generate(SimpleNamespace(content="ok"), None, settings)

        self.assertEqual(answer.temperature, 0.2)


class BuildModelTests(TestCase):
    """Temperature must only reach the API when it is actually configured."""

    def build(self, temperature):
        settings = SimpleNamespace(
            chat_model="claude-sonnet-5",
            max_tokens=1024,
            temperature=temperature,
            require_api_key=lambda: "sk-ant-test",
        )
        with patch("langchain_anthropic.ChatAnthropic") as chat:
            from ragcore.generator import build_model

            build_model(settings)
        return chat.call_args.kwargs

    def test_omits_temperature_when_unset(self):
        self.assertNotIn("temperature", self.build(None))

    def test_sends_temperature_when_set(self):
        self.assertEqual(self.build(0.2)["temperature"], 0.2)
