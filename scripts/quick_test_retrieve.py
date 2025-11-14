"""Quick test of retrieve endpoint"""
import requests
import json

# Test the retrieve endpoint
url = "http://localhost:8000/v1/retrieve"

# Test 1: Search products
print("Test 1: Searching products collection...")
response = requests.post(url, json={
    "query": "laptop with good battery life",
    "collection": "products",
    "top_k": 3
})

if response.status_code == 200:
    data = response.json()
    print(f"✅ Success! Found {data['num_results']} results in {data['latency_ms']:.2f}ms")
    for idx, doc in enumerate(data['results'][:2], 1):
        print(f"\n  Result {idx}:")
        print(f"    Distance: {doc['distance']:.4f}")
        print(f"    Text: {doc['text'][:100]}...")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)

# Test 2: Cross-collection search
print("\n\nTest 2: Cross-collection search...")
response = requests.post(url, json={
    "query": "customer support issue with refund",
    "top_k": 5
})

if response.status_code == 200:
    data = response.json()
    print(f"✅ Success! Found {data['num_results']} results in {data['latency_ms']:.2f}ms")
    collections_found = set(doc['collection'] for doc in data['results'])
    print(f"    Collections: {', '.join(collections_found)}")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)

print("\n✅ All tests completed!")
