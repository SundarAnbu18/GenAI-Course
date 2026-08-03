import os
import pickle
import faiss
from sentence_transformers import SentenceTransformer
from anthropic import Anthropic

api_key = os.environ.get('ANTHROPIC_API_KEY')
if not api_key:
    raise RuntimeError('ANTHROPIC_API_KEY environment variable is not set')

client = Anthropic(api_key=api_key)
model = SentenceTransformer('all-MiniLM-L6-v2')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
index = faiss.read_index(os.path.join(BASE_DIR, 'index.faiss'))
with open(os.path.join(BASE_DIR, 'docs.pkl'), 'rb') as f:
    docs = pickle.load(f)


def retrieve(query, k=3):
    query_embedding = model.encode([query], convert_to_numpy=True).astype('float32')
    _, indices = index.search(query_embedding, k)
    return [docs[i] for i in indices[0]]


def ask(query, k=3):
    context_docs = retrieve(query, k)
    context = "\n".join(context_docs)

    prompt = f"""Answer the question using only the context below. If the answer isn't in the context, say you don't know.

Context:
{context}

Question: {query}"""

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


if __name__ == "__main__":
    query = input("Ask a question: ")
    answer = ask(query)
    print("\nAnswer:")
    print(answer)
