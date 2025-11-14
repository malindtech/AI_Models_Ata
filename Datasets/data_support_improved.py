"""
Download customer support conversations with agent replies
Dataset: bitext/Bitext-customer-support-llm-chatbot-training-dataset
This dataset has proper customer queries AND agent responses
"""
import json
import os
from datasets import load_dataset

os.makedirs("data/raw/support", exist_ok=True)

print("Downloading Bitext Customer Support dataset...")
print("This dataset includes both customer queries AND agent responses")
print("Sampling diverse intents and categories...")

# Load full Bitext customer support dataset and sample diversely
ds_full = load_dataset("bitext/Bitext-customer-support-llm-chatbot-training-dataset", split="train")

# Get diverse sample by taking entries at intervals to ensure variety
total_size = len(ds_full)
step = total_size // 300  # Sample every Nth entry to get 300 diverse examples
indices = list(range(0, total_size, step))[:300]
ds = ds_full.select(indices)

support = []
for i, item in enumerate(ds):
    instruction = item.get("instruction", "").strip()  # Customer query
    response = item.get("response", "").strip()  # Agent response
    intent = item.get("intent", "").strip()
    category = item.get("category", "").strip()
    
    # Skip if missing critical fields
    if not instruction or not response:
        continue
    
    support.append({
        "id": f"support_{i:03}",
        "text": instruction,  # Customer message/query
        "agent_reply": response,  # Agent's response - THIS IS KEY!
        "metadata": {
            "source": "bitext_support",
            "intent": intent,
            "category": category
        }
    })

print(f"Total support conversations downloaded: {len(support)}")
print(f"✓ All entries have customer query AND agent reply")

# Check diversity
unique_intents = len(set(item['metadata']['intent'] for item in support))
unique_categories = len(set(item['metadata']['category'] for item in support))
print(f"✓ Unique intents: {unique_intents}")
print(f"✓ Unique categories: {unique_categories}")

print(f"\nSample entry:")
print(f"  Customer: {support[0]['text'][:80]}...")
print(f"  Agent: {support[0]['agent_reply'][:80]}...")

with open("data/raw/support/raw_support.json", "w", encoding="utf-8") as f:
    json.dump(support, f, indent=2)

print("\n✓ Saved to data/raw/support/raw_support.json")
print(f"✓ {len(support)} conversations with agent_reply field preserved")
