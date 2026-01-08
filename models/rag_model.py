from sentence_transformers import SentenceTransformer, util
from transformers import pipeline
import torch

# Embedding model for retrieval
embed_model = SentenceTransformer('all-MiniLM-L6-v2')
# LLM for generation
generator = pipeline("text-generation", model="gpt2")

# Precompute embeddings
def build_embeddings(destinations):
    for dest in destinations:
        dest['embedding'] = embed_model.encode(dest['description'], convert_to_tensor=True)
    return destinations

destinations_with_embeddings = build_embeddings(json.load(open('knowledge_base/destinations.json'))['destinations'])

def get_recommendations(query, destinations):
    query_embedding = embed_model.encode(query, convert_to_tensor=True)
    
    # Compute cosine similarity
    scores = []
    for dest in destinations:
        sim = util.cos_sim(query_embedding, dest['embedding']).item()
        scores.append((sim, dest))
    
    # Get top 3
    top_destinations = [d for s, d in sorted(scores, key=lambda x: x[0], reverse=True)[:3]]
    
    # Generate natural language summary using LLM
    recommendations = []
    for dest in top_destinations:
        prompt = f"Provide a friendly travel recommendation for: {dest['name']}, {dest['description']}"
        summary = generator(prompt, max_length=100, do_sample=True)[0]['generated_text']
        recommendations.append({'destination': dest, 'summary': summary})
    
    return recommendations
