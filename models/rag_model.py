import os
import json
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline
import torch
from math import radians, cos, sin, asin, sqrt
from functools import lru_cache
from langdetect import detect

# -------------------------------
# Setup paths
# -------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_PATH = os.path.join(BASE_DIR, 'knowledge_base', 'destinations.json')
GUIDES_PATH = os.path.join(BASE_DIR, 'knowledge_base', 'guides.json')
VEHICLES_PATH = os.path.join(BASE_DIR, 'knowledge_base', 'vehicles.json')
DRIVERS_PATH = os.path.join(BASE_DIR, 'knowledge_base', 'drivers.json')
# -------------------------------
# Load knowledge base
# -------------------------------
with open(KB_PATH, 'r', encoding='utf-8') as f:
    destinations_data = json.load(f)['destinations']

with open(GUIDES_PATH, 'r', encoding='utf-8') as f:
    guides_data = json.load(f)['guides']

with open(VEHICLES_PATH, 'r', encoding='utf-8') as f:
    vehicles_data = json.load(f)['vehicles']

with open(DRIVERS_PATH, 'r', encoding='utf-8') as f:
    drivers_data = json.load(f)['drivers']

def get_available_vehicles():
    """Return all available vehicles"""
    return [v for v in vehicles_data if v["available"]]

def estimate_fare(vehicle_id, distance_km):
    vehicle = next((v for v in vehicles_data if v["id"] == vehicle_id), None)
    if not vehicle:
        return None
    return vehicle["price_per_km"] * distance_km

def update_vehicle_availability(vehicle_id, available):
    for v in vehicles_data:
        if v["id"] == vehicle_id:
            v["available"] = available
    # Save back to JSON
    with open(VEHICLES_PATH, 'w', encoding='utf-8') as f:
        json.dump({"vehicles": vehicles_data}, f, ensure_ascii=False, indent=4)

# -------------------------------
# Embedding model for retrieval
# -------------------------------
#embed_model = SentenceTransformer('all-mpnet-base-v2')
embed_model = SentenceTransformer('sentence-transformers/distiluse-base-multilingual-cased-v2')

# LLM for text generation (RAG)
#generator = pipeline("text-generation", model="gpt2")
generator = pipeline(
    "text2text-generation",
    model="google/flan-t5-large",
    device=0 if torch.cuda.is_available() else -1
)


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
    Supports Sinhala or English responses based on the query language.
    """
    # Detect language of query
    try:
        lang = detect(query)
    except:
        lang = 'en'  # default to English if detection fails

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
        if lang == 'si':
            # Sinhala prompt
            prompt = (
                f"Provide a friendly travel recommendation in Sinhala letters for {dest['name']}. "
                f"Description: {dest['description']} "
                f"Keep it short and friendly."
            )
        else:
            # English prompt
            prompt = (
                f"Recommend {dest['name']} in Sri Lanka for a traveler. "
                f"Description: {dest['description']} "
                f"Keep it short and friendly."
            )

        summary = generator(
            prompt,
            max_new_tokens=80,
            do_sample=False
        )[0]["generated_text"]

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

@lru_cache(maxsize=128)
def generate_summary(prompt):
    return generator(prompt, max_new_tokens=60, do_sample=False)[0]["generated_text"]

def get_guides_for_destination(destination_name, user_district=None):
    matched_guides = []

    for guide in guides_data:
        if guide["destination"].lower() == destination_name.lower() and guide["available"]:
            if user_district:
                # Only include guides in the user's district
                if guide.get("district", "").lower() == user_district.lower():
                    matched_guides.append(guide)
            else:
                matched_guides.append(guide)

    return matched_guides


def generate_guide_pitch(guide):
    """
    Generate a short AI-based sales pitch for a tour guide
    """
    prompt = (
        f"Create a friendly and professional tour guide pitch.\n"
        f"Guide Name: {guide.get('name')}\n"
        f"Experience: {guide.get('experience')} years\n"
        f"Languages: {', '.join(guide.get('languages', []))}\n"
        f"Specialty: {guide.get('specialty')}\n"
        f"Destination: {guide.get('destination')}\n"
        f"Keep it short and persuasive."
    )

    return generator(
        prompt,
        max_new_tokens=60,
        do_sample=False
    )[0]["generated_text"]

def get_available_drivers(vehicle_type=None, user_district=None):
    available_drivers = []

    for driver in drivers_data:
        if not driver["available"]:
            continue

        vehicle = next(
            (v for v in vehicles_data if v["id"] == driver["vehicle_id"] and v["available"]),
            None
        )

        if not vehicle:
            continue

        if vehicle_type and vehicle["type"] != vehicle_type:
            continue

        if user_district and driver["district"].lower() != user_district.lower():
            continue

        available_drivers.append({
            "driver": driver,
            "vehicle": vehicle
        })

    return available_drivers

def get_driver_options(distance_km, vehicle_type=None, user_district=None):
    drivers = get_available_drivers(vehicle_type, user_district)

    results = []
    for item in drivers:
        fare = estimate_fare(item["vehicle"]["id"], distance_km)

        results.append({
            "driver_name": item["driver"]["name"],
            "phone": item["driver"]["phone"],
            "vehicle": item["vehicle"]["type"],
            "fare_estimate": round(fare, 2),
            "rating": item["driver"]["rating"]
        })

    return results
