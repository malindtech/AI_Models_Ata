import json, os
from datasets import load_dataset

os.makedirs("data/raw/reviews", exist_ok=True)

print("Downloading yelp_review_full dataset...")

ds = load_dataset("yelp_review_full")["train"].select(range(200))

reviews = []
for i, item in enumerate(ds):
    reviews.append({
        "id": f"review_{i:03}",
        "rating": int(item["label"]) + 1,  # convert 0–4 to 1–5 stars
        "text": item.get("text") or "",
    })

with open("data/raw/reviews/raw_reviews.json", "w", encoding="utf-8") as f:
    json.dump(reviews, f, indent=2)

print("Saved to data/raw/reviews/raw_reviews.json")
