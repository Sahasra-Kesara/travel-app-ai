import requests

def get_route(start_lat, start_lon, end_lat, end_lon):
    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
        "?overview=full"
        "&geometries=geojson"
        "&steps=true"
        "&alternatives=true"
    )

    response = requests.get(url)
    data = response.json()
    routes = []

    for route in data["routes"]:
        steps_list = []
        for leg in route["legs"]:
            for step in leg["steps"]:
                steps_list.append({
                    "name": step.get("name", ""),  # Road/Street Name
                    "instruction": step["maneuver"].get("instruction", ""),
                    "distance": step.get("distance", 0),
                    "duration": step.get("duration", 0),
                    "type": step["maneuver"].get("type", ""),
                    "modifier": step["maneuver"].get("modifier", "")
                })

        routes.append({
            "geometry": route["geometry"]["coordinates"],
            "distance": route["distance"],
            "duration": route["duration"],
            "steps": steps_list
        })

    return routes

def get_osrm_route(start, end, mode="car"):
    # Convert city names to coordinates if needed, or accept lat/lon
    # Call OSRM API and return geometry
    # Example for car mode:
    url = f"http://router.project-osrm.org/route/v1/driving/{start[1]},{start[0]};{end[1]},{end[0]}?overview=full&geometries=geojson"
    resp = requests.get(url)
    data = resp.json()
    if data.get("routes"):
        return data["routes"][0]["geometry"]["coordinates"]
    return []