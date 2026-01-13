from flask import Blueprint, render_template, request
from models.rag_model import get_recommendations, destinations_with_embeddings
from flask import render_template, request
from app.services.route_service import get_route
from models.rag_model import route_based_recommendation
import geoip2.database
from flask import request, render_template, flash
from flask import redirect
import requests
from models.rag_model import get_available_vehicles, estimate_fare, update_vehicle_availability, haversine
import requests

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

    # 1️⃣ Get start coordinates from city
    if start_city:
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": start_city,
                "format": "json",
                "limit": 1
            }
            response = requests.get(
                url,
                params=params,
                headers={"User-Agent": "TravelApp/1.0"}
            )
            data = response.json()
            if data:
                start_lat = float(data[0]["lat"])
                start_lon = float(data[0]["lon"])
            else:
                return f"City '{start_city}' not found.", 400
        except Exception as e:
            return f"Error fetching coordinates: {str(e)}", 500

    # 2️⃣ Fallback: GeoIP
    if start_lat is None or start_lon is None:
        try:
            reader = geoip2.database.Reader(GEOIP_DB_PATH)
            user_ip = request.remote_addr
            response = reader.city(user_ip)
            start_lat = response.location.latitude
            start_lon = response.location.longitude
            reader.close()
        except Exception:
            return "Cannot determine start location.", 400

    # 3️⃣ Destination coordinates
    try:
        end_lat = float(request.form["end_lat"])
        end_lon = float(request.form["end_lon"])
    except (ValueError, KeyError):
        return "Invalid destination coordinates.", 400

    # 4️⃣ Generate route + steps (UPDATED)
    route_data = get_route(start_lat, start_lon, end_lat, end_lon)

    route_coords = route_data["coordinates"]
    route_steps = route_data["steps"]

    # 5️⃣ Route-based recommendations
    query = "Suggest tourist destinations near this travel route in Sri Lanka"
    recommendations = route_based_recommendation(route_coords, query)

    # 6️⃣ Prepare destinations for JS
    destinations_for_js = []
    for r in recommendations:
        dest = r["destination"]
        destinations_for_js.append({
            "name": dest.get("name", ""),
            "category": dest.get("category", ""),
            "coordinates": dest.get("coordinates", {})
        })

    # 7️⃣ Send everything to frontend
    return render_template(
        "recommendations.html",
        results=recommendations or [],
        route_coords=route_coords or [],
        route_steps=route_steps or [],
        destinations=destinations_for_js or []
    )

@user_bp.route("/guides/<destination_name>")
def guides(destination_name):
    from models.rag_model import get_guides_for_destination, generate_guide_pitch

    # Try detecting district from user's IP
    user_ip = request.remote_addr
    user_district = None
    try:
        import geoip2.database
        reader = geoip2.database.Reader(GEOIP_DB_PATH)
        response = reader.city(user_ip)
        user_lat = response.location.latitude
        user_lon = response.location.longitude
        reader.close()
        user_district = get_district_from_coords(user_lat, user_lon)
    except Exception:
        pass

    guides = get_guides_for_destination(destination_name, user_district=user_district)


    # Add AI pitch
    for guide in guides:
        guide["ai_pitch"] = generate_guide_pitch(guide)

    return render_template(
        "guides.html",
        destination=destination_name,
        guides=guides
    )


def get_guides_for_destination(destination_name, user_district=None):
    matched_guides = []

    for guide in guides_data:
        if guide["destination"].lower() == destination_name.lower() and guide["available"]:
            if user_district:
                if guide.get("district", "").lower() == user_district.lower():
                    matched_guides.append(guide)
            else:
                matched_guides.append(guide)

    return matched_guides



@user_bp.route("/book-guide", methods=["POST"])
def book_guide():
    guide_id = request.form.get("guide_id")
    date = request.form.get("date")
    time = request.form.get("time")
    hours = request.form.get("hours")

    if not all([guide_id, date, time, hours]):
        flash("Please fill all booking details")
        return redirect(request.referrer)

    # Later: save to database
    flash("Guide booked successfully!")
    return redirect("/")

def get_district_from_coords(lat, lon):
    """Return the district (administrative area) for given coordinates"""
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

@user_bp.route("/vehicles")
def vehicles():
    available_vehicles = get_available_vehicles()

    # Generate static map URL (Google Static Maps)
    # Each vehicle will be a marker
    markers = []
    for v in available_vehicles:
        lat = v["coordinates"]["lat"]
        lon = v["coordinates"]["lon"]
        # Marker label will be the vehicle id (for reference)
        markers.append(f"color:red|label:{v['id']}|{lat},{lon}")

    # Google Static Maps URL
    map_url = ""
    if markers:
        markers_str = "&".join([f"markers={m}" for m in markers])
        map_url = (
            f"https://maps.googleapis.com/maps/api/staticmap?"
            f"size=600x400&{markers_str}&key=YOUR_GOOGLE_MAPS_API_KEY"
        )

    return render_template("vehicles.html", vehicles=available_vehicles, map_url=map_url)



@user_bp.route("/book-vehicle", methods=["POST"])
def book_vehicle():
    vehicle_id = request.form.get("vehicle_id")
    mobile = request.form.get("mobile")
    start_city = request.form.get("start_city")
    end_city = request.form.get("end_city")

    if not all([vehicle_id, mobile, start_city, end_city]):
        flash("Please fill all details")
        return redirect(request.referrer)

    # Convert cities to coordinates using Nominatim
    def get_coords(city):
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {"q": city, "format": "json", "limit": 1}
            response = requests.get(url, params=params, headers={"User-Agent": "TravelApp/1.0"})
            data = response.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
        except:
            pass
        return None, None

    start_lat, start_lon = get_coords(start_city)
    end_lat, end_lon = get_coords(end_city)

    if None in [start_lat, start_lon, end_lat, end_lon]:
        flash("Cannot find coordinates for start or destination. Check city names.")
        return redirect(request.referrer)

    # Calculate distance
    distance = haversine(start_lat, start_lon, end_lat, end_lon)

    # Calculate fare
    fare = estimate_fare(vehicle_id, distance)
    if fare is None:
        flash("Invalid vehicle selected")
        return redirect(request.referrer)

    # Update vehicle availability
    update_vehicle_availability(vehicle_id, False)

    # TODO: Save booking to DB along with mobile, distance, fare, cities
    flash(f"Vehicle booked successfully! Distance: {distance:.2f} km, Fare: LKR {fare:.2f}, Mobile: {mobile}")
    return redirect("/vehicles")