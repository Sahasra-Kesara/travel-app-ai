from app.services.route_service import get_osrm_route
import requests
import os
import geopandas as gpd

# Load railway shapefile once (GeoJSON or Shapefile)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAILWAY_SHAPEFILE = os.path.join(BASE_DIR, "data", "sri_lanka_railways.geojson")

# Check if file exists
if not os.path.exists(RAILWAY_SHAPEFILE):
    raise FileNotFoundError(f"Railway file not found: {RAILWAY_SHAPEFILE}")

railway_gdf = gpd.read_file(RAILWAY_SHAPEFILE)

def get_coords(city):
    """Get coordinates from Nominatim API"""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": city, "format": "json", "limit": 1}
        resp = requests.get(url, params=params, headers={"User-Agent": "TravelApp/1.0"})
        data = resp.json()
        if data:
            return float(data[0]["lon"]), float(data[0]["lat"])
    except:
        pass
    return None, None

def get_train_path(start, end):
    """Approximate train path using railway shapefile"""
    start_lon, start_lat = start
    end_lon, end_lat = end

    # Simple straight line for now (can later snap to nearest railway network)
    return [[start_lon, start_lat], [end_lon, end_lat]]

def build_route(segment):
    """Return route geometry array (lon, lat) for this segment"""
    mode = segment["mode"]
    start_lon, start_lat = get_coords(segment["from"])
    end_lon, end_lat = get_coords(segment["to"])

    if None in [start_lon, start_lat, end_lon, end_lat]:
        return [[80.7718, 7.8731], [80.2188, 6.0360]]

    if mode == "train":
        return get_train_path([start_lon, start_lat], [end_lon, end_lat])

    if mode == "bus":
        return get_osrm_route(segment["from"], segment["to"], "normal")

    if mode == "highway_car":
        return get_osrm_route(segment["from"], segment["to"], "highway")

    # normal_car
    return get_osrm_route(segment["from"], segment["to"], "normal")
