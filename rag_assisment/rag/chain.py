"""Task 4 — grounded prompt + Claude, composed with LCEL.

LangChain 1.x removed `langchain.chains`, so the legacy
create_retrieval_chain/create_stuff_documents_chain pair is gone. Composing the
prompt, model and parser with `|` is the current idiom — and it keeps retrieval,
augmentation and generation visible as three separate steps in answer().
"""

from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
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

# Same context, no grounding rules — the control condition for Task 4's
# "what happens if you remove the instruction?" experiment.
UNGROUNDED_PROMPT = "Answer the question.\n\nContext:\n{context}"


def format_docs(docs):
    """Retrieved Documents -> one numbered, cited block of prompt text.

    This is the 'augmentation' step. Numbering the chunks and naming their
    source file gives the model something concrete to cite.
    """
    return "\n\n".join(
        # .name strips the absolute path — DOCS_DIR is absolute, so the raw
        # metadata would leak the whole home directory into every citation.
        f"[{n}] ({Path(doc.metadata['source']).name})\n{doc.page_content}"
        for n, doc in enumerate(docs, start=1)
    )


def get_llm():
    load_env()  # ChatAnthropic reads ANTHROPIC_API_KEY from the environment
    return ChatAnthropic(model=LLM_MODEL, max_tokens=1024)


def build_chain(grounded=True):
    """prompt -> model -> string. `|` pipes each stage into the next."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT if grounded else UNGROUNDED_PROMPT),
        ("human", "{input}"),
    ])
    return prompt | get_llm() | StrOutputParser()


def answer(store, question, k=TOP_K, grounded=True):
    """Retrieve, augment, generate — returns the answer and the chunks used."""
    docs = store.similarity_search(question, k=k)
    text = build_chain(grounded).invoke(
        {"context": format_docs(docs), "input": question}
    )
    return {"answer": text, "context": docs}
