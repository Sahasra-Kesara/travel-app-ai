from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

import json, os
from models.rag_model import (
    get_recommendations,
    get_guides_for_destination,
    generate_guide_pitch,
    destinations_with_embeddings,
    destinations_near_route,
    haversine
)



admin_bp = Blueprint('admin', __name__, url_prefix="/admin")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST_PATH = os.path.join(BASE_DIR, "knowledge_base", "destinations.json")

# ---------------------------
# Dashboard
# ---------------------------
@admin_bp.route("/")
def dashboard():
    with open(DEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    destinations = data.get("destinations", [])
    return render_template("admin_dashboard.html", destinations=destinations)


# ---------------------------
# Add Destination
# ---------------------------
@admin_bp.route("/add-destination", methods=["GET", "POST"])
def add_destination():
    if request.method == "POST":
        with open(DEST_PATH, "r+", encoding="utf-8") as f:
            data = json.load(f)
        
        destination = {
            "id": f"dest_{len(data['destinations'])+1:03d}",
            "name": request.form["name"],
            "category": request.form["category"],
            "province": request.form.get("province", ""),
            "district": request.form.get("district", ""),
            "description": request.form["description"],
            "best_time_to_visit": request.form.get("best_time", ""),
            "entry_fee": request.form.get("entry_fee", ""),
            "duration": request.form.get("duration", ""),
            "activities": [act.strip() for act in request.form.get("activities", "").split(",")],
            "nearby_attractions": [att.strip() for att in request.form.get("nearby", "").split(",")],
            "coordinates": {
                "lat": float(request.form["lat"]),
                "lon": float(request.form["lon"])
            },
            "hotels": []  # empty list ready for hotels
        }

        data["destinations"].append(destination)
        f.seek(0)
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.truncate()

        flash("Destination added successfully!")
        return redirect(url_for("admin.dashboard"))

    return render_template("add_destination.html")


# ---------------------------
# Add Hotel
# ---------------------------
@admin_bp.route("/add-hotel", methods=["GET", "POST"])
def add_hotel():
    if request.method == "POST":
        hotel_name = request.form["name"]
        hotel = {
            "name": hotel_name,
            "owner": request.form["owner"],
            "mobile": request.form["mobile"],
            "price_per_night": request.form["price"],
            "description": request.form["description"]
        }

        dest_name = request.form["destination"]

        # Append hotel to the correct destination
        with open(DEST_PATH, "r+", encoding="utf-8") as f:
            data = json.load(f)
            for dest in data["destinations"]:
                if dest["name"].lower() == dest_name.lower():
                    dest["hotels"].append(hotel)
                    break
            else:
                flash(f"Destination '{dest_name}' not found. Add destination first!")
                return redirect(url_for("admin.add_hotel"))

            f.seek(0)
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.truncate()

        flash(f"Hotel '{hotel_name}' added successfully!")
        return redirect(url_for("admin.dashboard"))

    return render_template("add_hotel.html")

@admin_bp.route("/ai-assistant", methods=["POST"])
def ai_assistant():
    data = request.json
    query = data.get("query", "").strip()
    task_type = data.get("task_type", "recommend")

    if not query:
        return jsonify({"success": False, "message": "Query is empty!"})

    try:
        # ---------------- RECOMMEND ----------------
        if task_type == "recommend":
            results = get_recommendations(query, top_k=5)
            response = [{
                "name": r["destination"]["name"],
                "summary": r["summary"]
            } for r in results]

            return jsonify({"success": True, "results": response})

        # ---------------- TRIP ----------------
        elif task_type == "trip":
            parts = [p.strip() for p in query.lower().split("to")]
            if len(parts) < 2:
                return jsonify({
                    "success": True,
                    "results": [{"message": "Use format: Colombo to Kandy"}]
                })

            start = next((d for d in destinations_with_embeddings if parts[0] in d["name"].lower()), None)
            end = next((d for d in destinations_with_embeddings if parts[1] in d["name"].lower()), None)

            if not start or not end:
                return jsonify({
                    "success": True,
                    "results": [{"message": "Start or End location not found"}]
                })

            route_coords = [
                (start["coordinates"]["lon"], start["coordinates"]["lat"]),
                (end["coordinates"]["lon"], end["coordinates"]["lat"])
            ]

            nearby = destinations_near_route(route_coords, destinations_with_embeddings)
            trip_plan = get_recommendations(query, destinations=nearby, top_k=5)

            response = []
            for i, d in enumerate(trip_plan, start=1):
                dest = d["destination"]
                guides = get_guides_for_destination(dest["name"])
                guide_text = " | ".join([generate_guide_pitch(g) for g in guides])
                hotels = ", ".join([h["name"] for h in dest.get("hotels", [])])

                response.append({
                    "message": (
                        f"{i}. {dest['name']} ({dest['category']})\n"
                        f"📍 {dest.get('province','')}, {dest.get('district','')}\n"
                        f"✨ {dest.get('description','')}\n"
                        f"🏨 Hotels: {hotels or 'None'}\n"
                        f"🧑‍🏫 Guides: {guide_text or 'None'}"
                    ),
                    "lat": dest["coordinates"]["lat"],
                    "lon": dest["coordinates"]["lon"]
                })

            return jsonify({"success": True, "results": response})

        # ---------------- ADD DEST ----------------
        elif task_type == "add_dest":
            results = get_recommendations(query, top_k=1)
            if not results:
                return jsonify({"success": True, "results": [{"message": "No suggestion"}]})

            dest = results[0]["destination"]
            guides = get_guides_for_destination(dest["name"])

            response = [{
                "destination": {
                    "name": dest["name"],
                    "category": dest["category"],
                    "province": dest.get("province", ""),
                    "district": dest.get("district", ""),
                    "description": dest.get("description", ""),
                    "coordinates": dest.get("coordinates", {}),
                    "guides": [generate_guide_pitch(g) for g in guides]
                }
            }]

            return jsonify({"success": True, "results": response})

        return jsonify({"success": False, "message": "Unknown task"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
