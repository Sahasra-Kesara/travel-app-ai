import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from models.csv_loader import load_destinations

# Load model once
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Load CSV data
destinations = load_destinations()

# Convert text to embeddings
texts = [d["text"] for d in destinations]
embeddings = model.encode(texts, convert_to_numpy=True)

# Create FAISS index
dimension = embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)
index.add(embeddings)

def get_recommendations(query, top_k=5):
    query_vec = model.encode([query], convert_to_numpy=True)
    scores, indices = index.search(query_vec, top_k)

    results = []
    for idx in indices[0]:
        results.append(destinations[idx])

    return results