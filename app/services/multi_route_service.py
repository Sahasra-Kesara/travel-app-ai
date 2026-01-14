from app.services.route_service import get_osrm_route
import requests

# -------------------------------
# Convert city name to lon, lat
# -------------------------------
def get_coords(city):
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": city, "format": "json", "limit": 1}
        response = requests.get(url, params=params, headers={"User-Agent": "TravelApp/1.0"})
        data = response.json()
        if data:
            return float(data[0]["lon"]), float(data[0]["lat"])
    except:
        pass
    return None, None

# -------------------------------
# Build route geometry for a segment
# -------------------------------
def build_route(segment):
    mode = segment["mode"]

    start_lon, start_lat = get_coords(segment["from"])
    end_lon, end_lat = get_coords(segment["to"])

    if None in [start_lon, start_lat, end_lon, end_lat]:
        # fallback: straight line in Sri Lanka
        return [[80.7718, 7.8731], [80.2188, 6.0360]]

    if mode == "train":
        # TODO: replace with real train route if available
        return [[start_lon, start_lat], [end_lon, end_lat]]

    if mode == "bus":
        return get_osrm_route(segment["from"], segment["to"], "normal")

    if mode == "highway_car":
        return get_osrm_route(segment["from"], segment["to"], "highway")

    # normal car
    return [[start_lon, start_lat], [end_lon, end_lat]]
