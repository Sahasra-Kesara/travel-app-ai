from app.services.route_service import get_osrm_route
import requests
import os
import geopandas as gpd
from shapely.geometry import Point

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAILWAY_SHAPEFILE = os.path.join(BASE_DIR, "data", "sri_lanka_railways.geojson")
if not os.path.exists(RAILWAY_SHAPEFILE):
    raise FileNotFoundError(f"Railway file not found: {RAILWAY_SHAPEFILE}")

railway_gdf = gpd.read_file(RAILWAY_SHAPEFILE)

def get_coords(city):
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
    start_point = Point(start)
    end_point = Point(end)
    start_idx = railway_gdf.geometry.distance(start_point).sort_values().index[0]
    end_idx = railway_gdf.geometry.distance(end_point).sort_values().index[0]
    line_coords = list(railway_gdf.loc[start_idx:end_idx].geometry.unary_union.coords)
    return [[lon, lat] for lon, lat in line_coords]

def build_route(segment):
    mode = segment["mode"]
    start_lon, start_lat = get_coords(segment["from"])
    end_lon, end_lat = get_coords(segment["to"])
    if None in [start_lon, start_lat, end_lon, end_lat]:
        return [[80.7718, 7.8731], [80.2188, 6.0360]]

    if mode == "train":
        return get_train_path([start_lon, start_lat], [end_lon, end_lat])
    if mode in ["bus", "highway_car", "normal_car"]:
        return get_osrm_route([start_lat, start_lon], [end_lat, end_lon],
                              "highway" if mode=="highway_car" else "normal")
    return get_osrm_route([start_lat, start_lon], [end_lat, end_lon], "normal")
