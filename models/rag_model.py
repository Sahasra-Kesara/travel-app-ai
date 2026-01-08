import os
import json
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline
import torch
from math import radians, cos, sin, asin, sqrt

# -------------------------------
# Setup paths
# -------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_PATH = os.path.join(BASE_DIR, 'knowledge_base', 'destinations.json')

# -------------------------------
# Load knowledge base
# -------------------------------
with open(KB_PATH, 'r', encoding='utf-8') as f:
    destinations_data = json.load(f)['destinations']

# -------------------------------
# Embedding model for retrieval
# -------------------------------
embed_model = SentenceTransformer('all-MiniLM-L6-v2')

# LLM for text generation (RAG)
generator = pipeline("text-generation", model="gpt2")

# -------------------------------
# Precompute embeddings
# -------------------------------
def build_embeddings(destinations):
    for dest in destinations:
        # Convert description to vector embedding
        dest['embedding'] = embed_model.encode(dest['description'], convert_to_tensor=True)
    return destinations

# Apply embeddings once
destinations_with_embeddings = build_embeddings(destinations_data)

# -------------------------------
# RAG: Retrieve & Generate
# -------------------------------
def get_recommendations(query, destinations=destinations_with_embeddings, top_k=3):
    """
    Retrieve top_k destinations matching the query and generate friendly recommendations.
    """
    # Encode query
    query_embedding = embed_model.encode(query, convert_to_tensor=True)
    
    # Compute cosine similarity
    scores = []
    for dest in destinations:
        sim = util.cos_sim(query_embedding, dest['embedding']).item()
        scores.append((sim, dest))
    
    # Sort by similarity and take top_k
    top_destinations = [d for s, d in sorted(scores, key=lambda x: x[0], reverse=True)[:top_k]]
    
    # Generate friendly summaries using LLM
    recommendations = []
    for dest in top_destinations:
        prompt = f"Provide a friendly travel recommendation for: {dest['name']}, {dest['description']}"
        summary = generator(prompt, max_length=100, do_sample=True)[0]['generated_text']
        recommendations.append({'destination': dest, 'summary': summary})
    
    return recommendations

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c


def destinations_near_route(route_coords, destinations, max_distance_km=20):
    nearby = []

    for dest in destinations:
        dlat = dest["coordinates"]["lat"]
        dlon = dest["coordinates"]["lon"]

        for lon, lat in route_coords:
            if haversine(lat, lon, dlat, dlon) <= max_distance_km:
                nearby.append(dest)
                break

    return nearby

def route_based_recommendation(route_coords, query):
    nearby = destinations_near_route(
        route_coords,
        destinations_with_embeddings
    )

    return get_recommendations(
        query,
        destinations=nearby,
        top_k=5
    )
