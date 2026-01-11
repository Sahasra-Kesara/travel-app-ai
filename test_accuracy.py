# test_accuracy.py

from models.rag_model import get_recommendations, get_guides_for_destination

# -------------------------------
# Test Destinations
# -------------------------------
def test_destinations():
    queries = [
        ("Cultural tourism in Sri Lanka", ["Sigiriya", "Dambulla", "Polonnaruwa"]),
        ("Beach yoga in Weligama", ["Weligama", "Mirissa"])
    ]

    for query, ground_truth in queries:
        recs = get_recommendations(query)
        retrieved = [r['destination']['name'] for r in recs]
        correct = sum(1 for r in retrieved if r in ground_truth)
        acc = correct / len(ground_truth)
        print(f"Query: {query}, Accuracy: {acc:.2f}, Retrieved: {retrieved}")


# -------------------------------
# Test Guides
# -------------------------------
def test_guides():
    tests = [
        ("Weligama", "Matara", ["Nadeeka Samarawickrama"]),
        ("Kandy", None, ["Saman Perera", "Kumara Silva"])
    ]

    for dest, district, ground_truth in tests:
        recs = get_guides_for_destination(dest, district)
        retrieved = [g['name'] for g in recs]
        correct = sum(1 for r in retrieved if r in ground_truth)
        acc = correct / len(ground_truth)
        print(f"Destination: {dest}, District: {district}, Accuracy: {acc:.2f}, Retrieved: {retrieved}")


if __name__ == "__main__":
    print("=== Testing Destination Recommendations ===")
    test_destinations()
    print("\n=== Testing Guide Recommendations ===")
    test_guides()
