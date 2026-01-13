import requests

def get_route(start_lat, start_lon, end_lat, end_lon):
    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
        "?overview=full&geometries=geojson&steps=true"
    )

    response = requests.get(url)
    data = response.json()

    route = data["routes"][0]

    coordinates = route["geometry"]["coordinates"]
    steps = []

    for leg in route["legs"]:
        for step in leg["steps"]:
            steps.append({
                "instruction": step["maneuver"]["instruction"],
                "distance": step["distance"],
                "duration": step["duration"]
            })

    return {
        "coordinates": coordinates,
        "steps": steps
    }