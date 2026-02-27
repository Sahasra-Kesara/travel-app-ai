import os
import json
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline
import torch
from math import radians, cos, sin, asin, sqrt
from functools import lru_cache

# -------------------------------
# Setup paths
# -------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_PATH = os.path.join(BASE_DIR, 'knowledge_base', 'destinations.json')
GUIDES_PATH = os.path.join(BASE_DIR, 'knowledge_base', 'guides.json')
VEHICLES_PATH = os.path.join(BASE_DIR, 'knowledge_base', 'vehicles.json')
DRIVERS_PATH = os.path.join(BASE_DIR, 'knowledge_base', 'drivers.json')
BOOKINGS_PATH = os.path.join(BASE_DIR, 'knowledge_base', 'bookings.json')
HOTELS_PATH = os.path.join(BASE_DIR, 'knowledge_base', 'hotels.json')
HOSPITALS_PATH = os.path.join(BASE_DIR, 'knowledge_base', 'hospitals.json')

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

with open(HOTELS_PATH, 'r', encoding='utf-8') as f:
    hotels_data = json.load(f)['hotels']

with open(HOSPITALS_PATH, 'r', encoding='utf-8') as f:
    hospitals_data = json.load(f)['hospitals']
# -------------------------------
# Vehicle functions (unchanged)
# -------------------------------
def get_available_vehicles():
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

    with open(VEHICLES_PATH, 'w', encoding='utf-8') as f:
        json.dump({"vehicles": vehicles_data}, f, indent=4)


# -------------------------------
# Models
# -------------------------------
embed_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

generator = pipeline(
    "text2text-generation",
    model="google/flan-t5-large",
    device=0 if torch.cuda.is_available() else -1
)


# ============================================================
# STEP 1 — Location-aware embeddings (HIGH ACCURACY)
# ============================================================
def build_embeddings(destinations):
    for dest in destinations:
        search_text = f"""
        Name: {dest.get('name','')}
        Category: {dest.get('category','')}
        Province: {dest.get('province','')}
        District: {dest.get('district','')}
        Description: {dest.get('description','')}
        Activities: {', '.join(dest.get('activities', []))}
        Nearby: {', '.join(dest.get('nearby_attractions', []))}
        """

        dest['search_text'] = search_text.lower()

        dest['embedding'] = embed_model.encode(
            dest['search_text'],
            convert_to_tensor=True
        )

    return destinations


destinations_with_embeddings = build_embeddings(destinations_data)


# ============================================================
# STEP 2 — Location Pre-filter (Enterprise accuracy)
# ============================================================
def filter_by_location(query, destinations):
    q = query.lower()
    filtered = []

    for dest in destinations:
        if (
            dest.get("district","").lower() in q or
            dest.get("province","").lower() in q or
            dest.get("name","").lower() in q
        ):
            filtered.append(dest)

    return filtered if filtered else destinations


# ============================================================
# STEP 3 — Retrieval with Location Boosting
# ============================================================
def get_recommendations(query, destinations=destinations_with_embeddings, top_k=5):

    # Location pre-filter
    destinations = filter_by_location(query, destinations)

    query_embedding = embed_model.encode(query, convert_to_tensor=True)
    query_lower = query.lower()

    scores = []

    for dest in destinations:
        sim = util.cos_sim(query_embedding, dest['embedding']).item()

        # Location boosting
        if dest.get("district","").lower() in query_lower:
            sim += 0.30

        if dest.get("province","").lower() in query_lower:
            sim += 0.25

        if dest.get("name","").lower() in query_lower:
            sim += 0.40

        if dest.get("category","").lower() in query_lower:
            sim += 0.15

        scores.append((sim, dest))

    top_destinations = [
        d for s, d in sorted(scores, key=lambda x: x[0], reverse=True)[:top_k]
    ]

    # ========================================================
    # STEP 4 — Structured factual prompt (No hallucination)
    # ========================================================
    recommendations = []

    for dest in top_destinations:
        prompt = (
            f"Give a short travel recommendation in English.\n"
            f"Place: {dest['name']}\n"
            f"District: {dest['district']}\n"
            f"Province: {dest['province']}\n"
            f"Category: {dest['category']}\n"
            f"Best Time: {dest.get('best_time_to_visit','')}\n"
            f"Duration: {dest.get('duration','')}\n"
            f"Nearby: {', '.join(dest.get('nearby_attractions', []))}\n"
            f"Keep it short and factual."
        )

        summary = generator(
            prompt,
            max_new_tokens=60,
            do_sample=False
        )[0]["generated_text"]

        recommendations.append({
            "destination": dest,
            "summary": summary
        })

    return recommendations


# ============================================================
# Remaining functions (unchanged)
# ============================================================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
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

    return get_recommendations(query, destinations=nearby, top_k=5)


@lru_cache(maxsize=128)
def generate_summary(prompt):
    return generator(prompt, max_new_tokens=60, do_sample=False)[0]["generated_text"]

# ============================================================
# Guide Functions (FIX FOR IMPORT ERROR)
# ============================================================

def get_guides_for_destination(destination_name, user_district=None):
    """
    Return available guides for a destination.
    If user_district provided → prioritize same district.
    """
    matched_guides = []

    for guide in guides_data:
        if (
            guide.get("destination", "").lower() == destination_name.lower()
            and guide.get("available", False)
        ):
            if user_district:
                if guide.get("district", "").lower() == user_district.lower():
                    matched_guides.append(guide)
            else:
                matched_guides.append(guide)

    return matched_guides


def generate_guide_pitch(guide):
    """
    Generate short AI marketing pitch for a guide
    """
    prompt = (
        f"Write a short professional travel guide introduction.\n"
        f"Name: {guide.get('name','')}\n"
        f"Destination: {guide.get('destination','')}\n"
        f"Experience: {guide.get('experience','')} years\n"
        f"Languages: {', '.join(guide.get('languages', []))}\n"
        f"Keep it short and friendly."
    )

    return generate_summary(prompt)

def get_districts_along_route(route_coords, step=50):
    """
    Sample route points and detect districts.
    step = every Nth point to reduce API calls
    """
    districts = set()

    for i in range(0, len(route_coords), step):
        lon, lat = route_coords[i]
        district = get_district_from_coords(lat, lon)
        if district:
            districts.add(district.lower())

    return list(districts)

def get_guides_route_based(destination_name, route_coords):
    """
    Priority:
    1. Destination guides
    2. District guides along route
    """

    route_districts = get_districts_along_route(route_coords)

    matched = []

    for guide in guides_data:
        if not guide.get("available"):
            continue

        # Priority 1: Exact destination
        if guide.get("destination", "").lower() == destination_name.lower():
            matched.append(guide)
            continue

        # Priority 2: District along route
        if guide.get("district", "").lower() in route_districts:
            matched.append(guide)

    # Sort by rating
    matched = sorted(matched, key=lambda x: x.get("rating", 0), reverse=True)

    return matched