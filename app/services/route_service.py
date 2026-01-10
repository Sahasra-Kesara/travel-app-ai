import requests

def get_route(start_lat, start_lon, end_lat, end_lon):
    """
    Get route coordinates from OSRM routing service
    """
    url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}"
    
    params = {
        "overview": "full",
        "geometries": "geojson"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        # Check if request was successful
        if response.status_code != 200:
            print(f"OSRM API returned status code: {response.status_code}")
            print(f"Response text: {response.text}")
            return []
        
        # Check if response has content
        if not response.text:
            print("OSRM API returned empty response")
            return []
        
        # Try to parse JSON
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError as e:
            print(f"Failed to decode JSON: {e}")
            print(f"Response text: {response.text[:200]}")  # Print first 200 chars
            return []
        
        # Validate response structure
        if "routes" not in data or not data["routes"]:
            print("No routes found in response")
            return []
        
        # Extract coordinates
        coords = data["routes"][0]["geometry"]["coordinates"]
        
        # Convert to [lat, lon] format (OSRM returns [lon, lat])
        route_coords = [[coord[1], coord[0]] for coord in coords]
        
        return route_coords
        
    except requests.exceptions.Timeout:
        print("Request to OSRM API timed out")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error in get_route: {e}")
        return []
