from datasets import load_dataset
import json
import os

os.makedirs("data/raw", exist_ok=True)

# ----------------------------
# 1. CNN/DailyMail (works)
# ----------------------------
print("Downloading CNN/DailyMail...")
cnn = load_dataset("cnn_dailymail", "3.0.0", split="train[:200]")

cnn_out = []
for i, item in enumerate(cnn):
    cnn_out.append({
        "id": f"blog_cnn_{i:03}",
        "title": item["article"][:120].replace("\n", " ").strip(),
        "text": item["article"].strip(),
        "source": "cnn"
    })

with open("data/raw/raw_blogs_cnn.json", "w", encoding="utf-8") as f:
    json.dump(cnn_out, f, indent=2)

print("Saved raw_blogs_cnn.json")


# ----------------------------
# 2. CC-News (BEST long-form)
# ----------------------------
print("Downloading CC-News...")
news = load_dataset("cc_news", split="train[:200]")

news_out = []
for i, item in enumerate(news):
    title = item.get("title", "")
    text = item.get("text", "")

    if not text:
        continue

    news_out.append({
        "id": f"blog_news_{i:03}",
        "title": title[:120].replace("\n", " ").strip(),
        "text": text.strip(),
        "source": "cc_news"
    })

with open("data/raw/raw_blogs_news.json", "w", encoding="utf-8") as f:
    json.dump(news_out, f, indent=2)

print("Saved raw_blogs_news.json")
