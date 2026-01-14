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
    - Can combine train, bus, highway_car, normal_car
    - Returns segments with 'mode', 'from', 'to', 'geometry'
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
- Return ONLY JSON with segments including 'mode', 'from', 'to'

JSON format example:
{{
  "segments": [
    {{"mode": "train", "from": "Colombo Fort", "to": "Kandy"}},
    {{"mode": "bus", "from": "Kandy", "to": "Nuwara Eliya"}}
  ]
}}
Do NOT explain anything.
"""

    result = generator(prompt, max_new_tokens=350, do_sample=False)[0]["generated_text"]

    try:
        plan = json.loads(result)
    except Exception:
        # fallback single segment
        plan = {
            "segments": [{"mode": "normal_car", "from": start, "to": end}]
        }

    # Build geometry for each segment
    for seg in plan["segments"]:
        seg["geometry"] = build_route(seg)

    return plan
