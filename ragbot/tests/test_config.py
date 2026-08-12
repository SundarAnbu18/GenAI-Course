"""Settings come from the environment, so the parsing needs to be right."""

import os
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from ragcore.config import PROJECT_DIR, get_settings, load_env_file
from ragcore.exceptions import ConfigurationError


class SettingsTests(TestCase):
    def setUp(self):
        # Stub out .env loading: these tests are about how the environment is
        # read, and the repo's real .env would otherwise bleed into them.
        patcher = patch("ragcore.config.load_dotenv")
        patcher.start()
        self.addCleanup(patcher.stop)
        get_settings.cache_clear()
        self.addCleanup(get_settings.cache_clear)

    @patch.dict(os.environ, {}, clear=True)
    def test_defaults_live_inside_the_project(self):
        settings = get_settings()
        self.assertEqual(settings.documents_dir, PROJECT_DIR / "data" / "documents")
        self.assertEqual(settings.index_dir, PROJECT_DIR / "var" / "index")
        self.assertEqual(settings.top_k, 3)
        self.assertEqual(settings.chat_model, "claude-sonnet-5")

    @patch.dict(os.environ, {"RAG_TOP_K": "7", "RAG_CHAT_MODEL": "claude-opus-5"}, clear=True)
    def test_environment_overrides_defaults(self):
        settings = get_settings()
        self.assertEqual(settings.top_k, 7)
        self.assertEqual(settings.chat_model, "claude-opus-5")

    @patch.dict(os.environ, {"RAG_TOP_K": "three"}, clear=True)
    def test_a_non_numeric_top_k_is_a_configuration_error(self):
        with self.assertRaises(ConfigurationError):
            get_settings()

    @patch.dict(os.environ, {}, clear=True)
    def test_temperature_is_unset_by_default(self):
        # claude-sonnet-5 and the current Opus models reject a temperature
        # outright, so it must never be sent unless someone asks for it.
        self.assertIsNone(get_settings().temperature)

    @patch.dict(os.environ, {"RAG_TEMPERATURE": "0.2"}, clear=True)
    def test_temperature_can_be_configured(self):
        self.assertEqual(get_settings().temperature, 0.2)

    @patch.dict(os.environ, {"RAG_TEMPERATURE": "warm"}, clear=True)
    def test_a_non_numeric_temperature_is_a_configuration_error(self):
        with self.assertRaises(ConfigurationError):
            get_settings()

    @patch.dict(os.environ, {}, clear=True)
    def test_history_defaults_to_in_process_memory(self):
        settings = get_settings()

        self.assertEqual(settings.history_dsn, "")
        self.assertEqual(settings.history_turns, 6)

    @patch.dict(
        os.environ,
        {"RAG_HISTORY_DSN": "sqlite:///var/history.sqlite3", "RAG_HISTORY_TURNS": "2"},
        clear=True,
    )
    def test_history_can_be_pointed_at_a_database(self):
        settings = get_settings()

        self.assertEqual(settings.history_dsn, "sqlite:///var/history.sqlite3")
        self.assertEqual(settings.history_turns, 2)

    @patch.dict(os.environ, {"RAG_INDEX_DIR": "/tmp/rag-index"}, clear=True)
    def test_index_files_hang_off_the_index_directory(self):
        settings = get_settings()
        self.assertEqual(settings.index_path.name, "index.faiss")
        self.assertEqual(settings.chunks_path.name, "chunks.json")
        self.assertEqual(settings.index_path.parent, settings.index_dir)
        self.assertEqual(settings.chunks_path.parent, settings.index_dir)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_api_key_is_reported_clearly(self):
        with self.assertRaises(ConfigurationError):
            get_settings().require_api_key()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=True)
    def test_api_key_is_returned_when_present(self):
        self.assertEqual(get_settings().require_api_key(), "sk-ant-test")


class LoadEnvFileTests(TestCase):
    def _write(self, body: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / ".env"
        path.write_text(body, encoding="utf-8")
        return path

    @patch.dict(os.environ, {}, clear=True)
    def test_reads_pairs_and_strips_quotes(self):
        load_env_file(self._write('FOO=bar\nQUOTED="baz"\n'))
        self.assertEqual(os.environ["FOO"], "bar")
        self.assertEqual(os.environ["QUOTED"], "baz")

    @patch.dict(os.environ, {}, clear=True)
    def test_skips_comments_and_junk_lines(self):
        load_env_file(self._write("# a comment\n\nnot-a-pair\nFOO=bar\n"))
        self.assertEqual(list(os.environ), ["FOO"])

    @patch.dict(os.environ, {"FOO": "from-shell"}, clear=True)
    def test_the_real_environment_wins(self):
        load_env_file(self._write("FOO=from-file\n"))
        self.assertEqual(os.environ["FOO"], "from-shell")

    @patch.dict(os.environ, {}, clear=True)
    def test_a_missing_file_is_not_an_error(self):
        load_env_file(Path("/nonexistent/.env"))
        self.assertEqual(dict(os.environ), {})
