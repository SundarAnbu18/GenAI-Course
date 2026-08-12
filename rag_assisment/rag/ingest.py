"""Task 1 — load the PDFs and split them into overlapping chunks."""

from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import CHUNK_OVERLAP, CHUNK_SIZE, DOCS_DIR


def load_documents():
    """One Document per PDF *page*, with source/page in .metadata."""
    return PyPDFDirectoryLoader(str(DOCS_DIR)).load()


def split_documents(docs, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        add_start_index=True,
    )
    return splitter.split_documents(docs)


def load_chunks(size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    print("Loading documents...",split_documents(load_documents(), size, overlap))

    return split_documents(load_documents(), size, overlap)