"""Task 4 — grounded prompt + Claude, wired as a retrieval chain."""

from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from .config import LLM_MODEL, TOP_K, load_env

SYSTEM_PROMPT = """You answer questions using ONLY the context provided below.

Rules:
- If the answer is not in the context, reply exactly:
  "I don't know based on the provided documents."
- Never use outside knowledge, and never guess.
- End your answer with a line: Source: <filename(s) you used>

Context:
{context}"""

UNGROUNDED_PROMPT = "Answer the question.\n\nContext:\n{context}"


def get_llm():
    load_env()
    return ChatAnthropic(model=LLM_MODEL, max_tokens=1024)


def build_chain(store, k=TOP_K, grounded=True):
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT if grounded else UNGROUNDED_PROMPT),
        ("human", "{input}"),
    ])
    combine_docs = create_stuff_documents_chain(get_llm(), prompt)
    retriever = store.as_retriever(search_kwargs={"k": k})
    return create_retrieval_chain(retriever, combine_docs)