from models.rag_model import (
    route_based_recommendation,
    search_all_knowledge,
    get_guides_route_based,
    get_available_vehicles,
    estimate_fare,
    haversine,
    generate_summary
)
from app.services.route_service import get_route


def build_trip_response(start_lat, start_lon, end_lat, end_lon, destination_name=None):
    """
    Master function that builds full AI travel response
    """
    routes = get_route(start_lat, start_lon, end_lat, end_lon)

    if not routes:
        return {"error": "No routes found"}

    main_route = routes[0]
    route_geometry = main_route["geometry"]

    query = "Tourist attractions near this route in Sri Lanka"
    recommendations = route_based_recommendation(route_geometry, query)

    destinations = []
    for rec in recommendations:
        dest = rec["destination"]
        destinations.append({
            "name": dest.get("name"),
            "district": dest.get("district"),
            "category": dest.get("category"),
            "coordinates": dest.get("coordinates"),
            "summary": rec.get("summary")
        })

    hotels = []
    if destination_name:
        hotel_results = search_all_knowledge(destination_name)
        for item in hotel_results:
            if item["type"] == "hotel":
                h = item["data"]
                hotels.append({
                    "name": h.get("name"),
                    "district": h.get("district"),
                    "price_per_night": h.get("price_per_night"),
                    "amenities": h.get("amenities", [])
                })

    hospitals = []
    if destination_name:
        hospital_results = search_all_knowledge(destination_name)
        for item in hospital_results:
            if item["type"] == "hospital":
                m = item["data"]
                hospitals.append({
                    "name": m.get("name"),
                    "district": m.get("district"),
                    "specialties": m.get("specialties", [])
                })

    guides = []
    if destination_name:
        guide_results = get_guides_route_based(destination_name, route_geometry)

        for g in guide_results[:5]:
            guides.append({
                "id": g.get("id"),
                "name": g.get("name"),
                "district": g.get("district"),
                "languages": g.get("languages"),
                "rating": g.get("rating")
            })

    distance_km = haversine(start_lat, start_lon, end_lat, end_lon)

    vehicles = []
    available_vehicles = get_available_vehicles()

    for v in available_vehicles:
        fare = estimate_fare(v["id"], distance_km)
        vehicles.append({
            "id": v["id"],
            "type": v.get("type"),
            "seats": v.get("seats"),
            "price_per_km": v.get("price_per_km"),
            "estimated_fare": round(fare, 2) if fare else None
        })


    summary_prompt = f"""
    Create a short travel plan.

    Distance: {distance_km:.1f} km
    Destination: {destination_name}

    Nearby places:
    {', '.join([d['name'] for d in destinations[:3]])}

    Hotels available: {len(hotels)}
    Guides available: {len(guides)}
    Vehicles available: {len(vehicles)}
    Hospitals available: {len(hospitals)}

    Keep it short and professional.
    """

    summary = generate_summary(summary_prompt)

    # --------------------------------------------------
    # 9. Final Response
    # --------------------------------------------------
    return {
        "route": main_route,
        "distance_km": round(distance_km, 2),
        "destinations": destinations,
        "hotels": hotels,
        "guides": guides,
        "vehicles": vehicles,
        "hospitals": hospitals,
        "summary": summary
    }