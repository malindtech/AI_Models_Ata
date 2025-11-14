import json, random

def inspect(kind, count=10):
    print(f"\n=== Inspecting {kind} ===")
    data = json.load(open(f"data/cleaned/{kind}.json", "r", encoding="utf-8"))
    
    for item in random.sample(data, min(count, len(data))):
        print("\nID:", item["id"])
        print("TITLE:", item["title"])
        print("TEXT:", item["text"][:300], "...")
        print("-" * 80)

if __name__ == "__main__":
    inspect("blogs")
    inspect("products")
