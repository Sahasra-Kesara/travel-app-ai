import requests

def get_route(start_lat, start_lon, end_lat, end_lon):
    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
        "?overview=full&geometries=geojson"
    )

    response = requests.get(url)
    data = response.json()

    # coordinates = [[lon, lat], ...]
    return data["routes"][0]["geometry"]["coordinates"]
