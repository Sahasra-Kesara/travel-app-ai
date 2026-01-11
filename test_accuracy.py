import json
from models.rag_model import get_recommendations, destinations_with_embeddings, get_guides_for_destination

# -------------------------------
# Define test cases
# -------------------------------

# Destinations test: query -> expected top destinations
dest_test_cases = [
    {
        "query": "Cultural tourism in Sri Lanka",
        "expected": ["Sigiriya Rock Fortress", "Dambulla Cave Temple", "Polonnaruwa Ancient City"]
    },
    {
        "query": "Beach yoga in Weligama",
        "expected": ["Weligama Beach", "Dickwella Beach"]
    }
]

# Guides test: (destination, district) -> expected guides
guides_test_cases = [
    {
        "destination": "Sigiriya",
        "district": "Matale",
        "expected": ["Nimal Perera"]
    },
    {
        "destination": "Kandy",
        "district": None,
        "expected": ["Dinesh Wickramasinghe", "Sujatha Wickramasinghe"]
    }
]

# -------------------------------
# Helper function for accuracy
# -------------------------------
def accuracy(retrieved, expected):
    retrieved_set = set(retrieved)
    expected_set = set(expected)
    if not expected_set:
        return 0.0
    return len(retrieved_set & expected_set) / len(expected_set)

# -------------------------------
# Test destinations
# -------------------------------
print("=== Testing Destination Recommendations ===")
for case in dest_test_cases:
    results = get_recommendations(case["query"], destinations=destinations_with_embeddings, top_k=5)
    retrieved = [r['destination']['name'] for r in results]
    acc = accuracy(retrieved, case["expected"])
    print(f"Query: {case['query']}, Accuracy: {acc:.2f}, Retrieved: {retrieved}")

# -------------------------------
# Test guides
# -------------------------------
print("\n=== Testing Guide Recommendations ===")
for case in guides_test_cases:
    retrieved = [g['name'] for g in get_guides_for_destination(case["destination"], case["district"])]
    acc = accuracy(retrieved, case["expected"])
    print(f"Destination: {case['destination']}, District: {case['district']}, Accuracy: {acc:.2f}, Retrieved: {retrieved}")
