from app.services.route_service import get_osrm_route

def build_route(segment):
    mode = segment["mode"]

    if mode == "train":
        return get_train_route(segment["from"], segment["to"])

    if mode == "bus":
        return get_osrm_route(segment["from"], segment["to"], "normal")

    if mode == "highway_car":
        return get_osrm_route(segment["from"], segment["to"], "highway")

    return get_osrm_route(segment["from"], segment["to"], "normal")
