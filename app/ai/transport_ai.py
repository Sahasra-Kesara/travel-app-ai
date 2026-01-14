import json
from transformers import pipeline
import torch
from app.services.multi_route_service import build_route

# Load LLM
generator = pipeline(
    "text2text-generation",
    model="google/flan-t5-large",
    device=0 if torch.cuda.is_available() else -1
)

def ai_transport_plan(destinations):
    """
    Multi-modal AI planner for multiple destinations.
    Returns segments connecting each destination in order.
    """
    segments = []

    for i in range(len(destinations)-1):
        start = destinations[i]
        end = destinations[i+1]

        prompt = f"""
You are a smart Sri Lanka trip planner AI.

Start: {start}
End: {end}

Available transport modes:
- train
- bus
- highway_car
- normal_car

Rules:
- Prefer train for long distances if railway exists
- Use highway_car if expressways shorten the route
- Use bus to connect train stations to destinations
- Combine multiple transport modes if needed
- Suggest intermediate stops/destinations along the way
- Return ONLY JSON with segments including 'mode', 'from', 'to', 'stops' (array of strings)
"""

        result = generator(prompt, max_new_tokens=400, do_sample=False)[0]["generated_text"]

        try:
            plan = json.loads(result)
        except Exception:
            plan = {"segments": [{"mode": "normal_car", "from": start, "to": end, "stops": []}]}

        # Build geometry
        for seg in plan["segments"]:
            seg["geometry"] = build_route(seg)
            segments.append(seg)

    return {"segments": segments}
