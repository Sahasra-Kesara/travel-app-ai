import pandas as pd

CSV_PATH = "knowledge_base/destinations.csv"

def load_destinations():
    df = pd.read_csv(CSV_PATH)

    destinations = []

    for _, row in df.iterrows():
        activities = [
            row.get("activities/0", ""),
            row.get("activities/1", ""),
            row.get("activities/2", ""),
            row.get("activities/3", "")
        ]

        nearby = [
            row.get("nearby_attractions/0", ""),
            row.get("nearby_attractions/1", ""),
            row.get("nearby_attractions/2", ""),
            row.get("nearby_attractions/3", "")
        ]

        text = f"""
        {row['name']} in {row['district']}, {row['province']}.
        Category: {row['category']}.
        Description: {row['description']}.
        Activities: {', '.join([a for a in activities if pd.notna(a)])}.
        Nearby: {', '.join([n for n in nearby if pd.notna(n)])}.
        Best time: {row['best_time_to_visit']}.
        """

        destinations.append({
            "id": row["id"],
            "name": row["name"],
            "category": row["category"],
            "province": row["province"],
            "district": row["district"],
            "description": row["description"],
            "coordinates": {
                "lat": row["coordinates/lat"],
                "lon": row["coordinates/lon"]
            },
            "text": text
        })

    return destinations