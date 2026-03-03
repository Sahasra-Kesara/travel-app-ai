import os
import json
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline
import torch
from math import radians, cos, sin, asin, sqrt
from functools import lru_cache
import re

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
TOURISM_PATH = os.path.join(BASE_DIR, 'knowledge_base', 'tourism.json')

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

with open(TOURISM_PATH, 'r', encoding='utf-8') as f:
    tourism_data = json.load(f) 

# ---- Build global index ----
def build_global_index():
    index = []

    # Destinations
    for d in destinations_data:
        text = f"{d['name']} {d['category']} {d['district']} {d['description']}"
        emb = embed_model.encode(text, convert_to_tensor=True)

        index.append({
            "type": "destination",
            "data": d,
            "embedding": emb
        })

    # Hotels
    for h in hotels_data:
        text = f"{h['name']} hotel {h['district']} price {h['price_per_night']} amenities {' '.join(h.get('amenities', []))}"
        emb = embed_model.encode(text, convert_to_tensor=True)

        index.append({
            "type": "hotel",
            "data": h,
            "embedding": emb
        })

    # Hospitals
    for m in hospitals_data:
        text = f"{m['name']} hospital {m['district']} specialties {' '.join(m.get('specialties', []))}"
        emb = embed_model.encode(text, convert_to_tensor=True)

        index.append({
            "type": "hospital",
            "data": m,
            "embedding": emb
        })

    # Guides
    for g in guides_data:
        text = f"{g['name']} guide {g['destination']} {g['district']} languages {' '.join(g.get('language', []))}"
        emb = embed_model.encode(text, convert_to_tensor=True)

        index.append({
            "type": "guide",
            "data": g,
            "embedding": emb
        })

    # Tourism Locations
    for t in tourism_data:
        text = f"{t['name']} {t['category']} {t['province']} {t['district']} {t['description']} activities {' '.join(t.get('activities', []))}"
        emb = embed_model.encode(text, convert_to_tensor=True)

        index.append({
            "type": "tourism",
            "data": t,
            "embedding": emb
        })

    return index


# ---- Search function ----
def search_all_knowledge(query, top_k=10):
    query_embedding = embed_model.encode(query, convert_to_tensor=True)
    q_lower = query.lower()

    # small helper: check if any keyword present
    def contains_any(text, keywords):
        t = text.lower()
        return any(k in t for k in keywords)

    # mapping keywords to tourism categories for boosting
    keyword_category_map = {
        'cultural': 'Cultural & Heritage Sites',
        'heritage': 'Cultural & Heritage Sites',
        'temple': 'Cultural & Heritage Sites',
        'fort': 'Cultural & Heritage Sites',
        'ancient': 'Cultural & Heritage Sites',
        'nature': 'Nature & Adventure',
        'waterfall': 'Nature & Adventure',
        'hike': 'Nature & Adventure',
        'park': 'Nature & Adventure',
        'beach': 'Nature & Adventure',
        'tea': 'Tea & Spice Shops',
        'spice': 'Tea & Spice Shops',
        'food': 'Authentic Food Places',
        'restaurant': 'Authentic Food Places',
        'experience': 'Local Experiences',
        'cooking': 'Local Experiences',
        'village': 'Local Experiences',
        'ayurveda': 'Ayurveda & Wellness',
        'spa': 'Ayurveda & Wellness',
        'atm': 'ATMs & Currency Exchange',
        'sim': 'SIM Card / Telecom Shops',
        'station': 'Transport Hubs'
    }

    scores = []
    for item in global_knowledge_index:
        sim = util.cos_sim(query_embedding, item["embedding"]).item()
        # boosting for tourism entries
        if item["type"] == "tourism":
            data = item["data"]
            cat = data.get("category", "").lower()
            # boost if query mentions category keywords
            for kw, target_cat in keyword_category_map.items():
                if kw in q_lower and target_cat.lower() == cat:
                    sim += 0.15  # small nudge
                    break
            # boost when activity matches query
            activities = " ".join(data.get("activities", []))
            if contains_any(activities, q_lower.split()):
                sim += 0.1
        scores.append((sim, item))

    results = [
        item for score, item in sorted(scores, key=lambda x: x[0], reverse=True)
    ]

    # 🔴 STRICT DISTRICT FILTER (after ranking)
    filtered = []
    district = extract_district_from_query(query)

    if district:
        for item in results:
            if item["data"].get("district", "").lower() == district:
                filtered.append(item)

        # If district mentioned but nothing found → return empty
        return filtered[:top_k]

    # No district mentioned → normal
    return results[:top_k]

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

# Build once at startup
global_knowledge_index = build_global_index()

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
    # STRICT district filtering
    district = extract_district_from_query(query)
    if district:
        destinations = [
            d for d in destinations
            if d.get("district", "").lower() == district
        ]

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

def get_district_from_coords(lat, lon):
    """Return the district (administrative area) for given coordinates using Nominatim."""
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "zoom": 10,  # Administrative area level
            "addressdetails": 1
        }
        response = requests.get(url, params=params, headers={"User-Agent": "TravelApp/1.0"})
        data = response.json()
        # District in Sri Lanka is usually "county" or "state_district" in OSM
        district = data.get("address", {}).get("county") or data.get("address", {}).get("state_district")
        return district
    except Exception:
        return None

def get_districts_along_route(route_coords, step=50):
    from app.routes_user import get_district_from_coords
    districts = set()
    for i in range(0, len(route_coords), step):
        lon, lat = route_coords[i]
        district = get_district_from_coords(lat, lon)
        if district:
            districts.add(district.lower())
    return list(districts)

# ============================================================
# STRICT DISTRICT LIST (Sri Lanka)
# ============================================================
SRI_LANKA_DISTRICTS = [
    "colombo","gampaha","kalutara",
    "kandy","matale","nuwara eliya",
    "galle","matara","hambantota",
    "jaffna","kilinochchi","mannar","vavuniya","mullaitivu",
    "batticaloa","ampara","trincomalee",
    "kurunegala","puttalam",
    "anuradhapura","polonnaruwa",
    "badulla","monaragala",
    "ratnapura","kegalle"
]


def extract_district_from_query(query):
    q = query.lower()
    for d in SRI_LANKA_DISTRICTS:
        if d in q:
            return d
    return None

def strict_district_filter(query, items):
    """
    Only return items where district EXACTLY matches query district.
    No description-based matching.
    """
    district = extract_district_from_query(query)

    if not district:
        return items  # No district mentioned → normal search

    filtered = []

    for item in items:
        item_district = item.get("district", "").lower()

        # Exact match only
        if item_district == district:
            filtered.append(item)

    return filtered

def detect_user_intent(query):
    q = query.lower()

    route_keywords = [
        "route", "how to go", "travel from", "directions",
        "distance from", "path", "way to"
    ]

    detail_keywords = [
        "tell me about", "details", "information",
        "best places", "recommend", "what to see",
        "hotels", "guides", "hospitals"
    ]

    if any(k in q for k in route_keywords):
        return "route"

    if any(k in q for k in detail_keywords):
        return "details"

    return "general"

def extract_cities(query):
    pattern = r"from (.*?) to (.*)"
    match = re.search(pattern, query.lower())
    if match:
        return match.group(1), match.group(2)
    return None, None

def generate_human_response(query, results):
    context = ""

    for item in results[:3]:
        data = item["data"]
        context += f"""
        Name: {data.get('name')}
        District: {data.get('district')}
        Category: {data.get('category')}
        Description: {data.get('description')}
        """

    prompt = f"""
    You are a friendly Sri Lanka travel assistant.

    User question:
    {query}

    Relevant information:
    {context}

    Answer naturally like a human.
    Include helpful travel tips.
    Suggest nearby places or services.
    Keep it under 120 words.
    """

    return generator(prompt, max_new_tokens=120, do_sample=False)[0]["generated_text"]