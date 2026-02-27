from flask import Blueprint, render_template, request, jsonify
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
from app.ai.transport_ai import ai_transport_plan
from app.services.multi_route_service import build_route
from models.rag_model import get_guides_route_based
from models.rag_model import search_all_knowledge
from app.services.trip_response_builder import build_trip_response

GEOIP_DB_PATH = "geoip/GeoLite2-City.mmdb"
user_bp = Blueprint('user', __name__)

@user_bp.route('/')
def home():
    # Just show search page
    return render_template('home.html')

@user_bp.route("/trip-planner")
def trip_planner():
    return render_template("customer_dashboard.html")


@user_bp.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')

    if not query:
        return render_template('destination.html', results=[])

    raw_results = search_all_knowledge(query)

    results = []
    for item in raw_results:
        results.append({
            "type": item["type"],
            "data": item["data"]
        })

    return render_template('destination.html', results=results)

@user_bp.route("/plan", methods=["POST"])
def plan_trip():
    start_city = request.form.get("start_city")
    start_lat = None
    start_lon = None

    # Get start coordinates from city
    if start_city:
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {"q": start_city, "format": "json", "limit": 1}
            response = requests.get(url, params=params, headers={"User-Agent": "TravelApp/1.0"})
            data = response.json()
            if data:
                start_lat = float(data[0]["lat"])
                start_lon = float(data[0]["lon"])
            else:
                return f"City '{start_city}' not found.", 400
        except Exception as e:
            return f"Error fetching coordinates: {str(e)}", 500

    # If no city, try GeoIP
    if start_lat is None or start_lon is None:
        try:
            reader = geoip2.database.Reader(GEOIP_DB_PATH)
            user_ip = request.remote_addr
            response = reader.city(user_ip)
            start_lat = response.location.latitude
            start_lon = response.location.longitude
            reader.close()
        except Exception:
            return "Cannot determine start location. Please enter a city.", 400

    # Destination coordinates
    try:
        end_lat = float(request.form["end_lat"])
        end_lon = float(request.form["end_lon"])
    except ValueError:
        return "Invalid destination coordinates.", 400

    # Get routes from OSRM
    routes = get_route(start_lat, start_lon, end_lat, end_lon)
    if not routes:
        return "No routes found.", 500

    main_route = routes[0]

    destination_name = request.form.get("destination_name")
    guides = []
    if destination_name:
        guides = get_guides_route_based(
            destination_name,
            main_route["geometry"]
        )

    alternative_routes = routes[1:]

    # Route-based AI recommendations
    query = "Suggest tourist destinations near this travel route in Sri Lanka"
    recommendations = route_based_recommendation(main_route["geometry"], query)
    
    # Prepare destinations for JS map
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
        route_main=main_route,
        route_alternatives=alternative_routes,
        results=recommendations,
        destinations=destinations_for_js,
        guides=guides
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

@user_bp.route("/guide/<guide_id>")
def guide_details(guide_id):
    from models.rag_model import guides_data

    guide = next((g for g in guides_data if g["id"] == guide_id), None)

    if not guide:
        return "Guide not found", 404

    return render_template("guide_details.html", guide=guide)

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


# -------------------------------
# AI Trip Plan Endpoint
# -------------------------------
@user_bp.route("/ai-trip-plan", methods=["POST"])
def ai_trip_plan_route():
    data = request.get_json()
    start = data.get("start")
    end = data.get("end")
    if not start or not end:
        return jsonify({"error": "Start and end required"}), 400

    plan = ai_transport_plan(start, end)
    return jsonify(plan)

# -------------------------------
# Route Geometry Endpoint
# -------------------------------
@user_bp.route("/route", methods=["GET"])
def get_route_endpoint():
    start = request.args.get("from")
    end = request.args.get("to")
    mode = request.args.get("mode")
    if not all([start, end, mode]):
        return jsonify([])

    coords = build_route({"from": start, "to": end, "mode": mode})
    return jsonify(coords)

