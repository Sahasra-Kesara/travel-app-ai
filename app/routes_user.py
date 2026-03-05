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
import re

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
        return render_template('destination.html', results_by_type={}, map_items=[])

    raw_results = search_all_knowledge(query)

    results_by_type = {
        "destinations": [],
        "guides": [],
        "vehicles": [],
        "drivers": [],
        "bookings": [],
        "hotels": [],
        "hospitals": [],
        "tourism": []
    }

    map_items = []

    for item in raw_results:
        data = item["data"]
        type_key = item["type"] + "s"  # plural key
        if type_key in results_by_type:
            results_by_type[type_key].append(data)

        # Only add items that have coordinates for the map
        if "coordinates" in data:
            map_items.append({
                "type": item["type"],
                "name": data.get("name"),
                "lat": data["coordinates"]["lat"],
                "lon": data["coordinates"]["lon"],
                "district": data.get("district", ""),
                "description": data.get("description", "")
            })

    return render_template(
        'destination.html',
        results_by_type=results_by_type,
        map_items=map_items
    )

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
        guides=guides,
        route_geometry=main_route["geometry"]
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

@user_bp.route("/full-trip-plan", methods=["POST"])
def full_trip_plan():
    data = request.get_json()

    start_city = data.get("start_city")
    destination_name = data.get("destination")

    if not start_city or not destination_name:
        return jsonify({"error": "Start city and destination required"}), 400

    # Convert cities to coordinates
    def get_coords(city):
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": city, "format": "json", "limit": 1}
        res = requests.get(url, params=params, headers={"User-Agent": "TravelApp/1.0"})
        data = res.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
        return None, None

    start_lat, start_lon = get_coords(start_city)
    end_lat, end_lon = get_coords(destination_name)

    if None in [start_lat, start_lon, end_lat, end_lon]:
        return jsonify({"error": "Location not found"}), 400

    result = build_trip_response(
        start_lat,
        start_lon,
        end_lat,
        end_lon,
        destination_name
    )

    return jsonify(result)

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

# ==============================
# AI Auto Suggest Endpoint
# ==============================
@user_bp.route("/suggest", methods=["GET"])
def suggest():
    query = request.args.get("q", "").strip().lower()

    if len(query) < 2:
        return jsonify([])

    # Predefined smart prompts (ChatGPT-style)
    smart_phrases = [
        "best places to visit in ella",
        "hotels near sigiriya under 10000",
        "best route from colombo to kandy",
        "tour guides available in galle",
        "vehicle from colombo to arugam bay",
        "hospitals near nuwara eliya"
    ]

    results = [p for p in smart_phrases if p.startswith(query)]

    # Also add semantic matches
    kb_results = search_all_knowledge(query, top_k=3)
    for item in kb_results:
        name = item["data"].get("name", "")
        if name and name.lower().startswith(query):
            results.append(name)

    return jsonify(results[:5])

# ==============================
# ChatGPT-level AI Autocomplete
# ==============================
@user_bp.route("/ai-autocomplete", methods=["GET"])
def ai_autocomplete():
    query = request.args.get("q", "").strip()

    if len(query) < 3:
        return jsonify([])

    try:
        # Detect intent keywords
        lower_q = query.lower()

        intent_hint = ""
        if "hotel" in lower_q:
            intent_hint = "Complete this travel query about hotels."
        elif "route" in lower_q or "travel" in lower_q:
            intent_hint = "Complete this travel route question."
        elif "guide" in lower_q:
            intent_hint = "Complete this query about tour guides."
        elif "hospital" in lower_q:
            intent_hint = "Complete this query about hospitals."
        elif "vehicle" in lower_q or "transport" in lower_q:
            intent_hint = "Complete this transportation query."
        else:
            intent_hint = "Complete this Sri Lanka travel query naturally."

        # AI prompt
        prompt = f"""
        {intent_hint}
        User started typing: "{query}"
        Complete it as a natural search sentence.
        Keep it under 15 words.
        """

        suggestion = generator(
            prompt,
            max_new_tokens=30,
            do_sample=False
        )[0]["generated_text"]

        # Clean output
        suggestion = suggestion.replace(prompt, "").strip()

        # Also add KB-based completions
        kb_results = search_all_knowledge(query, top_k=3)
        kb_names = [
            item["data"].get("name")
            for item in kb_results
            if item["data"].get("name")
        ]

        results = [suggestion] + kb_names

        # Remove duplicates
        results = list(dict.fromkeys(results))

        return jsonify(results[:5])

    except Exception as e:
        return jsonify([])



@user_bp.route('/smart-search', methods=['POST'])
def smart_search():
    query = request.form.get("query")
    intent = detect_user_intent(query)

    # ROUTE MODE
    if intent == "route":
        start, end = extract_cities(query)
        if start and end:
            return redirect(url_for("user.plan_trip",
                                    start_city=start,
                                    destination_name=end))

    # DETAIL MODE
    results = search_all_knowledge(query)
    ai_answer = generate_human_response(query, results)

    return render_template(
        "recommendations.html",
        results_by_type=group_results(results),
        ai_answer=ai_answer
    )


@user_bp.route('/chat', methods=['POST'])
def chat():
    """
    Chat endpoint for intelligent travel assistant agent
    Handles queries about destinations, routes, guides, hotels, vehicles, hospitals, and trip planning
    """
    from app.chat_agent import chat_agent
    
    data = request.get_json()
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({
            'response': 'Please ask me something! I can help with destinations, routes, guides, hotels, vehicles, hospitals, and trip planning.'
        })
    
    try:
        # Process message through the chat agent
        response = chat_agent.process_message(message)
        
        return jsonify({
            'response': response,
            'status': 'success'
        })
    except Exception as e:
        print(f"Chat error: {str(e)}")
        return jsonify({
            'response': 'I encountered an error processing your request. Please try again with a different question!',
            'status': 'error',
            'error': str(e)
        }), 200  # Return 200 to prevent fetch from failing

@user_bp.route('/voice', methods=['POST'])
def voice_chat():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file'}), 400
    
    audio_file = request.files['audio']
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name
    
    try:
        from models.speech_to_text import transcribe_audio
        text = transcribe_audio(tmp_path)
        
        if not text:
            return jsonify({'error': 'Could not transcribe audio'}), 400
        
        from models.chat_agent import chat_agent
        response = chat_agent.process_message(text)
        return jsonify({'transcription': text, 'response': response})
    finally:
        os.unlink(tmp_path)