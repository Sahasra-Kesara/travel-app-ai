from flask import Blueprint, render_template, request
from models.rag_model import get_recommendations, destinations_with_embeddings
from flask import render_template, request
from app.services.route_service import get_route
from models.rag_model import route_based_recommendation
import geoip2.database
from flask import request, render_template, flash

GEOIP_DB_PATH = "geoip/GeoLite2-City.mmdb"
user_bp = Blueprint('user', __name__)

@user_bp.route('/')
def home():
    # Just show search page
    return render_template('home.html')

@user_bp.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')

    if not query:
        return render_template('destination.html', results=[])

    # Use RAG knowledge base with embeddings
    results = get_recommendations(
        query,
        destinations=destinations_with_embeddings
    )

    return render_template('destination.html', results=results)

import requests

@user_bp.route("/plan", methods=["POST"])
def plan_trip():
    start_city = request.form.get("start_city")
    start_lat = None
    start_lon = None

    # If user provided a city, use Nominatim API to get coordinates
    if start_city:
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": start_city,
                "format": "json",
                "limit": 1
            }
            response = requests.get(url, params=params, headers={"User-Agent": "TravelApp/1.0"})
            data = response.json()
            if data:
                start_lat = float(data[0]["lat"])
                start_lon = float(data[0]["lon"])
            else:
                return f"City '{start_city}' not found. Please enter a valid city.", 400
        except Exception as e:
            return f"Error fetching coordinates for city: {str(e)}", 500

    # If no city provided, try GeoIP
    if start_lat is None or start_lon is None:
        try:
            reader = geoip2.database.Reader(GEOIP_DB_PATH)
            user_ip = request.remote_addr
            response = reader.city(user_ip)
            start_lat = response.location.latitude
            start_lon = response.location.longitude
            reader.close()
        except Exception:
            return "Cannot determine start location. Please enter a city manually.", 400

    # Destination coordinates from form
    try:
        end_lat = float(request.form["end_lat"])
        end_lon = float(request.form["end_lon"])
    except ValueError:
        return "Invalid destination coordinates.", 400

    # Generate route
    route_coords = get_route(start_lat, start_lon, end_lat, end_lon)
    query = "Suggest tourist destinations near this travel route in Sri Lanka"
    recommendations = route_based_recommendation(route_coords, query)

    # Prepare destinations for JS
    destinations_for_js = []
    for r in recommendations:
        dest = r["destination"]
        destinations_for_js.append({
            "name": dest.get("name", ""),
            "category": dest.get("category", ""),
            "coordinates": dest.get("coordinates", {})
        })

    return render_template(
        "recommendations.html",
        results=recommendations or [],
        route_coords=route_coords or [],
        destinations=destinations_for_js or []
    )