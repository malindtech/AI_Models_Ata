import json, os
from datasets import load_dataset

os.makedirs("data/raw/social", exist_ok=True)

print("Downloading go_emotions dataset...")

ds = load_dataset("go_emotions")["train"].select(range(200))

social = []
for i, item in enumerate(ds):
    social.append({
        "id": f"social_{i:03}",
        "text": item.get("text") or "",
        "labels": item.get("labels") or []  # list of emotion categories encoded
    })

with open("data/raw/social/raw_social.json", "w", encoding="utf-8") as f:
    json.dump(social, f, indent=2)

print("Saved to data/raw/social/raw_social.json")
