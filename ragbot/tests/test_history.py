"""Conversation storage: ids are untrusted input, and reads must stay bounded."""

from types import SimpleNamespace
from unittest import TestCase

from langchain_core.messages import AIMessage, HumanMessage

from ragcore import history as history_module
from ragcore.history import (
    forget,
    get_history,
    is_valid_conversation_id,
    recent_messages,
    record_turn,
)

ID = "3f2504e0-4f89-41d3-9a0c-0305e82c3301"
OTHER_ID = "9c858901-8a57-4791-81fe-4c455b099bc9"

# In-memory backend; a DSN would point at a real database.
SETTINGS = SimpleNamespace(history_dsn="", history_turns=2)


class ConversationIdTests(TestCase):
    def test_accepts_a_uuid(self):
        self.assertTrue(is_valid_conversation_id(ID))

    def test_rejects_anything_else(self):
        # These become keys in a shared store, so nothing else gets through.
        for bad in ["", "  ", "abc", "../../etc/passwd", ID + "x", "a" * 500]:
            with self.subTest(value=bad):
                self.assertFalse(is_valid_conversation_id(bad))


class StoreTests(TestCase):
    def setUp(self):
        history_module._MEMORY.clear()
        self.addCleanup(history_module._MEMORY.clear)

    def test_the_same_id_gets_the_same_store(self):
        self.assertIs(get_history(ID, SETTINGS), get_history(ID, SETTINGS))

    def test_conversations_do_not_leak_into_each_other(self):
        record_turn(get_history(ID, SETTINGS), "who?", "Sundar.")

        self.assertEqual(get_history(OTHER_ID, SETTINGS).messages, [])

    def test_a_turn_is_stored_as_a_question_and_an_answer(self):
        store = get_history(ID, SETTINGS)

        record_turn(store, "who?", "Sundar.")

        self.assertEqual([type(m) for m in store.messages], [HumanMessage, AIMessage])
        self.assertEqual([m.content for m in store.messages], ["who?", "Sundar."])

    def test_forget_drops_the_conversation(self):
        record_turn(get_history(ID, SETTINGS), "who?", "Sundar.")

        forget(ID, SETTINGS)

        self.assertEqual(get_history(ID, SETTINGS).messages, [])


class RecentMessagesTests(TestCase):
    def setUp(self):
        history_module._MEMORY.clear()
        self.addCleanup(history_module._MEMORY.clear)
        self.store = get_history(ID, SETTINGS)
        for i in range(5):
            record_turn(self.store, f"q{i}", f"a{i}")

    def test_returns_only_the_last_few_turns(self):
        # history_turns=2 means the last two exchanges, four messages.
        recent = recent_messages(self.store, SETTINGS)

        self.assertEqual([m.content for m in recent], ["q3", "a3", "q4", "a4"])

    def test_zero_turns_disables_history_entirely(self):
        off = SimpleNamespace(history_dsn="", history_turns=0)

        self.assertEqual(recent_messages(self.store, off), [])
