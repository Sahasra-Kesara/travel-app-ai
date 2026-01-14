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

def ai_transport_plan(start, end):
    """
    Multi-modal AI planner:
    - Combines train → bus → highway_car → normal_car
    - Suggests intermediate stops/destinations
    - Returns segments with 'mode', 'from', 'to', 'geometry', 'stops'
    """
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

JSON format example:
{{
  "segments": [
    {{
      "mode": "train",
      "from": "Colombo Fort",
      "to": "Kandy",
      "stops": ["Pettah", "Polgahawela"]
    }},
    {{
      "mode": "bus",
      "from": "Kandy",
      "to": "Nuwara Eliya",
      "stops": ["Ambewela"]
    }}
  ]
}}
Do NOT explain anything.
"""

    result = generator(prompt, max_new_tokens=400, do_sample=False)[0]["generated_text"]

    try:
        plan = json.loads(result)
    except Exception:
        plan = {"segments": [{"mode": "normal_car", "from": start, "to": end, "stops": []}]}

    # Build real road geometry for each segment
    for seg in plan["segments"]:
        seg["geometry"] = build_route(seg)

    return plan
