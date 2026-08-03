import faiss
import pickle
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

with open('data/document.txt', 'r') as f:
    docs = [line.strip() for line in f.readlines() if line.strip()]

print(f"Number of documents read: {len(docs)}")

embeddings = model.encode(docs, convert_to_numpy=True)

dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings.astype('float32'))

faiss.write_index(index, 'index.faiss')

with open('docs.pkl', 'wb') as f:
    pickle.dump(docs, f)

print(f"Index built with {index.ntotal} vectors and saved to index.faiss")
