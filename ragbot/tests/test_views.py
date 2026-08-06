"""The HTTP contract: what the widget and the browser can rely on.

``answer_question`` is mocked throughout — these tests are about validation,
status codes and error handling, not about retrieval quality.
"""

import json
import logging
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from ragcore.chunking import Chunk
from ragcore.exceptions import IndexNotBuiltError
from ragcore.generator import Answer
from ragcore.store import SearchResult

ANSWER_TARGET = "chatbot.views.answer_question"
CONVERSATION_ID = "3f2504e0-4f89-41d3-9a0c-0305e82c3301"


def an_answer(text="Bengaluru.") -> Answer:
    """The views receive an Answer object now, not a bare string."""
    return Answer(
        text=text,
        model="claude-sonnet-5",
        temperature=None,
        input_tokens=12,
        output_tokens=3,
        stop_reason="end_turn",
        sources=[SearchResult(Chunk(text="alpha", source="document.txt"), distance=0.1)],
    )


class QuietLogsMixin:
    """Several tests deliberately trigger errors; their tracebacks are not news."""

    def setUp(self):
        super().setUp()
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


class AskApiTests(QuietLogsMixin, SimpleTestCase):
    def post(self, body, **headers):
        return self.client.post(
            reverse("ask_api"),
            data=body if isinstance(body, str) else json.dumps(body),
            content_type="application/json",
            **headers,
        )

    @patch(ANSWER_TARGET, return_value=an_answer("Sundar is an engineer."))
    def test_returns_the_answer(self, mocked):
        response = self.post({"question": "who is sundar?"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "Sundar is an engineer.")
        mocked.assert_called_once_with("who is sundar?", conversation_id=None)

    @patch(ANSWER_TARGET, return_value=an_answer())
    def test_returns_the_metadata_alongside_the_answer(self, mocked):
        payload = self.post({"question": "where?"}).json()

        self.assertEqual(payload["model"], "claude-sonnet-5")
        self.assertIsNone(payload["temperature"])
        self.assertEqual(payload["usage"], {"input_tokens": 12, "output_tokens": 3})
        self.assertEqual(payload["sources"][0]["source"], "document.txt")

    @patch(ANSWER_TARGET, return_value=an_answer("ok"))
    def test_strips_surrounding_whitespace(self, mocked):
        self.post({"question": "  spaced  "})

        mocked.assert_called_once_with("spaced", conversation_id=None)

    @patch(ANSWER_TARGET, return_value=an_answer())
    def test_passes_a_conversation_id_through_and_echoes_it_back(self, mocked):
        response = self.post({"question": "and his cloud skills?", "conversation_id": CONVERSATION_ID})

        mocked.assert_called_once_with(
            "and his cloud skills?", conversation_id=CONVERSATION_ID
        )
        self.assertEqual(response.json()["conversation_id"], CONVERSATION_ID)

    @patch(ANSWER_TARGET, return_value=an_answer())
    def test_omits_the_conversation_id_when_none_was_sent(self, mocked):
        self.assertNotIn("conversation_id", self.post({"question": "who?"}).json())

    @patch(ANSWER_TARGET)
    def test_rejects_a_conversation_id_that_is_not_a_uuid(self, mocked):
        # It becomes a key in a shared store, so it is validated not trusted.
        for bad in ["../../etc/passwd", "abc", 12345]:
            with self.subTest(value=bad):
                response = self.post({"question": "who?", "conversation_id": bad})

                self.assertEqual(response.status_code, 400)
                self.assertIn("conversation_id", response.json()["error"])
        mocked.assert_not_called()

    def test_rejects_a_missing_question(self):
        response = self.post({})

        self.assertEqual(response.status_code, 400)
        self.assertIn("required", response.json()["error"])

    def test_rejects_a_blank_question(self):
        self.assertEqual(self.post({"question": "   "}).status_code, 400)

    def test_rejects_a_non_string_question(self):
        self.assertEqual(self.post({"question": 42}).status_code, 400)

    def test_rejects_a_json_body_that_is_not_an_object(self):
        self.assertEqual(self.post(["question"]).status_code, 400)

    def test_rejects_malformed_json(self):
        self.assertEqual(self.post("{not json").status_code, 400)

    def test_rejects_an_over_long_question(self):
        response = self.post({"question": "x" * 1001})

        self.assertEqual(response.status_code, 400)
        self.assertIn("1000", response.json()["error"])

    def test_rejects_get(self):
        self.assertEqual(self.client.get(reverse("ask_api")).status_code, 405)

    @override_settings(WIDGET_API_KEY="s3cret")
    def test_requires_the_api_key_when_one_is_configured(self):
        self.assertEqual(self.post({"question": "hi"}).status_code, 401)
        self.assertEqual(self.post({"question": "hi"}, HTTP_X_API_KEY="wrong").status_code, 401)

    @override_settings(WIDGET_API_KEY="s3cret")
    @patch(ANSWER_TARGET, return_value=an_answer("ok"))
    def test_accepts_the_correct_api_key(self, mocked):
        response = self.post({"question": "hi"}, HTTP_X_API_KEY="s3cret")

        self.assertEqual(response.status_code, 200)

    @patch(ANSWER_TARGET, side_effect=IndexNotBuiltError("no index"))
    def test_a_cold_index_is_a_503(self, mocked):
        response = self.post({"question": "hi"})

        self.assertEqual(response.status_code, 503)
        # The operator-facing detail belongs in the logs, not the response.
        self.assertNotIn("no index", response.json()["error"])

    @patch(ANSWER_TARGET, side_effect=RuntimeError("boom"))
    def test_an_unexpected_failure_is_a_500_without_details(self, mocked):
        response = self.post({"question": "hi"})

        self.assertEqual(response.status_code, 500)
        self.assertNotIn("boom", response.json()["error"])


class ChatPageTests(QuietLogsMixin, SimpleTestCase):
    def test_get_renders_the_form(self):
        response = self.client.get(reverse("chat"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<form")

    @patch(ANSWER_TARGET, return_value=an_answer())
    def test_post_shows_the_answer(self, mocked):
        response = self.client.post(reverse("chat"), {"question": "where?"})

        self.assertContains(response, "Bengaluru.")

    @patch(ANSWER_TARGET, side_effect=IndexNotBuiltError("no index"))
    def test_post_shows_a_friendly_error(self, mocked):
        response = self.client.post(reverse("chat"), {"question": "where?"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "unavailable")
        self.assertNotContains(response, "no index")

    @patch(ANSWER_TARGET)
    def test_an_empty_question_never_reaches_the_pipeline(self, mocked):
        self.client.post(reverse("chat"), {"question": "   "})

        mocked.assert_not_called()

    @patch(ANSWER_TARGET, return_value=an_answer())
    def test_the_input_is_empty_after_an_answer(self, mocked):
        response = self.client.post(reverse("chat"), {"question": "where?"})

        # The textarea must come back empty rather than repeating the question.
        self.assertContains(response, "></textarea>")
        self.assertNotContains(response, "where?</textarea>")


class ChatPageBackgroundPostTests(QuietLogsMixin, SimpleTestCase):
    """The page posts in the background so it can show a loader meanwhile."""

    def post(self, question, **extra):
        return self.client.post(
            reverse("chat"),
            dict({"question": question}, **extra),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    @patch(ANSWER_TARGET, return_value=an_answer())
    def test_passes_a_conversation_id_through(self, mocked):
        response = self.post("and his skills?", conversation_id=CONVERSATION_ID)

        mocked.assert_called_once_with("and his skills?", conversation_id=CONVERSATION_ID)
        self.assertEqual(response.json()["conversation_id"], CONVERSATION_ID)

    @patch(ANSWER_TARGET)
    def test_rejects_a_conversation_id_that_is_not_a_uuid(self, mocked):
        response = self.post("who?", conversation_id="not-a-uuid")

        self.assertEqual(response.status_code, 400)
        mocked.assert_not_called()

    @patch(ANSWER_TARGET, return_value=an_answer())
    def test_returns_json_rather_than_a_page(self, mocked):
        response = self.post("where?")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "Bengaluru.")

    def test_rejects_an_empty_question(self):
        self.assertEqual(self.post("   ").status_code, 400)

    @patch(ANSWER_TARGET, side_effect=IndexNotBuiltError("no index"))
    def test_a_cold_index_is_a_503(self, mocked):
        response = self.post("where?")

        self.assertEqual(response.status_code, 503)
        self.assertNotIn("no index", response.json()["error"])

    @patch(ANSWER_TARGET, side_effect=RuntimeError("boom"))
    def test_an_unexpected_failure_is_a_500(self, mocked):
        response = self.post("where?")

        self.assertEqual(response.status_code, 500)
        self.assertNotIn("boom", response.json()["error"])

    def test_a_get_still_renders_the_page(self):
        response = self.client.get(reverse("chat"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<form")


class HealthTests(QuietLogsMixin, SimpleTestCase):
    def test_reports_missing_index(self):
        with patch("chatbot.views.get_settings") as mocked:
            mocked.return_value.index_path.is_file.return_value = False
            mocked.return_value.chunks_path.is_file.return_value = False
            response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "index-missing")

    def test_reports_ok_when_the_index_is_on_disk(self):
        with patch("chatbot.views.get_settings") as mocked:
            mocked.return_value.index_path.is_file.return_value = True
            mocked.return_value.chunks_path.is_file.return_value = True
            response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
