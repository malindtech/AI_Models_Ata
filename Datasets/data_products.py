"""
Download Amazon product reviews with proper titles
Dataset: amazon_polarity - High quality Amazon reviews with titles and content
"""
import json
import os
from datasets import load_dataset

os.makedirs("data/raw/products", exist_ok=True)

print("Downloading amazon_polarity dataset (Amazon product reviews)...")
print("This dataset has proper title and content fields with good quality data")

# Load Amazon reviews dataset - has title and content fields
ds = load_dataset("amazon_polarity", split="train[:200]")

products = []
for i, item in enumerate(ds):
    title = item.get("title", "").strip()
    content = item.get("content", "").strip()
    label = item.get("label", 0)  # 0=negative, 1=positive
    
    # Skip if missing critical fields
    if not title or not content:
        continue
    
    products.append({
        "id": f"prod_{i:03}",
        "title": title,  # Proper product title preserved
        "text": content,  # Review/description content
        "metadata": {
            "source": "amazon_polarity",
            "rating": "positive" if label == 1 else "negative"
        }
    })

print(f"Total products downloaded: {len(products)}")
print(f"Sample product title: {products[0]['title'][:80]}...")

with open("data/raw/products/raw_products.json", "w", encoding="utf-8") as f:
    json.dump(products, f, indent=2)

print("✓ Saved to data/raw/products/raw_products.json")
print(f"✓ All {len(products)} products have non-empty titles")
