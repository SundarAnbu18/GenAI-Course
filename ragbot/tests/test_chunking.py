"""Chunking is the one piece of retrieval quality we control outright."""

from unittest import TestCase

from ragcore.chunking import Chunk, chunk_document, split_paragraphs


class SplitParagraphsTests(TestCase):
    def test_splits_on_blank_lines(self):
        self.assertEqual(split_paragraphs("first\n\nsecond"), ["first", "second"])

    def test_collapses_whitespace_inside_a_paragraph(self):
        self.assertEqual(split_paragraphs("a  line\nwrapped   oddly"), ["a line wrapped oddly"])

    def test_drops_blank_paragraphs(self):
        self.assertEqual(split_paragraphs("one\n\n   \n\ntwo"), ["one", "two"])

    def test_empty_document_yields_nothing(self):
        self.assertEqual(split_paragraphs("   \n\n  "), [])


class ChunkDocumentTests(TestCase):
    def test_every_chunk_carries_its_source(self):
        chunks = chunk_document("alpha\n\nbeta", source="document.txt")
        self.assertEqual([c.text for c in chunks], ["alpha", "beta"])
        self.assertEqual({c.source for c in chunks}, {"document.txt"})

    def test_round_trips_through_dict(self):
        original = Chunk(text="hello", source="a.md")
        self.assertEqual(Chunk.from_dict(original.to_dict()), original)

    def test_from_dict_tolerates_a_missing_source(self):
        self.assertEqual(Chunk.from_dict({"text": "hello"}).source, "")
