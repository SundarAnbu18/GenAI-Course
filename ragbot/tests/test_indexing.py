"""Corpus discovery — which files get indexed, and what happens when none do."""

import dataclasses
import tempfile
from pathlib import Path
from unittest import TestCase

from ragcore.config import get_settings
from ragcore.exceptions import NoDocumentsError
from ragcore.indexing import iter_document_paths, load_chunks


class DocumentDiscoveryTests(TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def _settings(self):
        # Reuse the real defaults, but point the corpus at the temp directory.
        return dataclasses.replace(get_settings(), documents_dir=self.root)

    def test_finds_txt_and_md_and_ignores_everything_else(self):
        (self.root / "b.txt").write_text("b", encoding="utf-8")
        (self.root / "a.md").write_text("a", encoding="utf-8")
        (self.root / "notes.pdf").write_text("skip me", encoding="utf-8")

        self.assertEqual([p.name for p in iter_document_paths(self.root)], ["a.md", "b.txt"])

    def test_searches_subdirectories(self):
        nested = self.root / "clients" / "acme"
        nested.mkdir(parents=True)
        (nested / "kickoff.md").write_text("hello", encoding="utf-8")

        self.assertEqual([p.name for p in iter_document_paths(self.root)], ["kickoff.md"])

    def test_a_missing_directory_yields_nothing(self):
        self.assertEqual(iter_document_paths(self.root / "nope"), [])

    def test_chunks_are_collected_across_files(self):
        (self.root / "one.txt").write_text("alpha\n\nbeta", encoding="utf-8")
        (self.root / "two.txt").write_text("gamma", encoding="utf-8")

        chunks = load_chunks(self._settings())

        self.assertEqual([c.text for c in chunks], ["alpha", "beta", "gamma"])
        self.assertEqual([c.source for c in chunks], ["one.txt", "one.txt", "two.txt"])

    def test_an_empty_corpus_is_an_error_rather_than_an_empty_index(self):
        with self.assertRaises(NoDocumentsError):
            load_chunks(self._settings())

    def test_whitespace_only_documents_are_an_error_too(self):
        (self.root / "blank.txt").write_text("   \n\n  ", encoding="utf-8")

        with self.assertRaises(NoDocumentsError):
            load_chunks(self._settings())
