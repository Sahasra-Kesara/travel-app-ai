from flask import Blueprint, render_template, request, redirect, url_for, flash
import json, os
from rag_model import (
    get_recommendations, get_guides_for_destination, generate_guide_pitch,
    destinations_with_embeddings, destinations_near_route, haversine
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
