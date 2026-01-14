import json
from transformers import pipeline
import torch

# -------------------------------
# Load LLM
# -------------------------------
generator = pipeline(
    "text2text-generation",
    model="google/flan-t5-large",
    device=0 if torch.cuda.is_available() else -1
)

# -------------------------------
# AI Transport Planner
# -------------------------------
def ai_transport_plan(start, end):
    """
    Decide transport modes and segments for Sri Lanka trips
    Returns structured JSON (NO sentences)
    """

    prompt = f"""
You are an intelligent Sri Lanka trip planner AI.

Start location: {start}
End location: {end}

Available transport modes:
- train
- bus
- highway_car
- normal_car

Rules:
- Prefer train for long distances if railway exists
- Use highway_car if expressways help
- Use bus to connect train stations to destinations
- Combine transport modes if needed

Return ONLY valid JSON.
Do NOT explain anything.

JSON format:
{{
  "segments": [
    {{
      "mode": "train",
      "from": "Colombo Fort",
      "to": "Kandy"
    }}
  ]
}}
"""

    result = generator(
        prompt,
        max_new_tokens=250,
        do_sample=False
    )[0]["generated_text"]

    try:
        return json.loads(result)
    except Exception:
        # fallback (VERY IMPORTANT)
        return {
            "segments": [
                {
                    "mode": "normal_car",
                    "from": start,
                    "to": end
                }
            ]
        }
