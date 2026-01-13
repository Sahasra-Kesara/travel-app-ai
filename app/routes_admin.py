from flask import Blueprint, render_template, request, redirect, url_for, flash
import json
import os

admin_bp = Blueprint('admin', __name__, url_prefix="/admin")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOTEL_PATH = os.path.join(BASE_DIR, "knowledge_base", "hotels.json")
DEST_PATH = os.path.join(BASE_DIR, "knowledge_base", "destinations.json")

@admin_bp.route("/")
def dashboard():
    return render_template("admin_dashboard.html")

# ---------------------------
# Add Hotel
# ---------------------------
@admin_bp.route("/add-hotel", methods=["GET", "POST"])
def add_hotel():
    if request.method == "POST":
        hotel = {
            "name": request.form["name"],
            "owner": request.form["owner"],
            "mobile": request.form["mobile"],
            "destination": request.form["destination"],
            "price_per_night": request.form["price"],
            "description": request.form["description"]
        }

        with open(HOTEL_PATH, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["hotels"].append(hotel)
            f.seek(0)
            json.dump(data, f, indent=4, ensure_ascii=False)

        flash("Hotel added successfully!")
        return redirect(url_for("admin.dashboard"))

    return render_template("add_hotel.html")


# ---------------------------
# Add Destination
# ---------------------------
@admin_bp.route("/add-destination", methods=["GET", "POST"])
def add_destination():
    if request.method == "POST":
        destination = {
            "name": request.form["name"],
            "category": request.form["category"],
            "description": request.form["description"],
            "coordinates": {
                "lat": float(request.form["lat"]),
                "lon": float(request.form["lon"])
            }
        }

        with open(DEST_PATH, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["destinations"].append(destination)
            f.seek(0)
            json.dump(data, f, indent=4, ensure_ascii=False)

        flash("Destination added successfully!")
        return redirect(url_for("admin.dashboard"))

    return render_template("add_destination.html")
