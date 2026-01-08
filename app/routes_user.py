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

@user_bp.route("/plan", methods=["POST"])
def plan_trip():
    # Try to get start location from form
    start_lat = request.form.get("start_lat")
    start_lon = request.form.get("start_lon")

    # If form does not have start location, use GeoIP
    if not start_lat or not start_lon:
        try:
            import geoip2.database
            reader = geoip2.database.Reader(GEOIP_DB_PATH)
            user_ip = request.remote_addr
            response = reader.city(user_ip)
            start_lat = response.location.latitude
            start_lon = response.location.longitude
            reader.close()
        except Exception as e:
            # GeoIP failed
            return "Cannot determine start location. Please provide a starting location.", 400

    # Convert to float
    start_lat = float(start_lat)
    start_lon = float(start_lon)
    end_lat = float(request.form["end_lat"])
    end_lon = float(request.form["end_lon"])

    # Generate route
    route_coords = get_route(start_lat, start_lon, end_lat, end_lon)
    query = "Suggest tourist destinations near this travel route in Sri Lanka"
    recommendations = route_based_recommendation(route_coords, query)

    # Prepare data for JS
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