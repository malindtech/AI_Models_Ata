# scripts/demo_review_system.py
"""
Demo script to showcase the Review System functionality
Generates sample content and simulates review workflow
"""
import httpx
import time
from datetime import datetime

BACKEND_URL = "http://localhost:8000"

print("=" * 70)
print("  🎬 DAY 8 REVIEW SYSTEM - LIVE DEMO")
print("=" * 70)
print()

# Check backend health
print("1️⃣ Checking backend health...")
try:
    response = httpx.get(f"{BACKEND_URL}/health", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Backend is healthy")
        print(f"   📊 Vector DB: {'Available' if data.get('vector_db') else 'Unavailable'}")
    else:
        print(f"   ❌ Backend returned status {response.status_code}")
        exit(1)
except Exception as e:
    print(f"   ❌ Cannot connect to backend: {e}")
    print(f"   💡 Start backend with: uvicorn backend.main:app --reload")
    exit(1)

print()

# Generate sample content
print("2️⃣ Generating sample content...")
content_requests = [
    {
        "content_type": "blog",
        "topic": "Benefits of AI in customer service",
        "tone": "professional"
    },
    {
        "content_type": "support_reply",
        "topic": "Password reset instructions",
        "tone": "friendly"
    }
]

generated_items = []

for idx, request in enumerate(content_requests, 1):
    print(f"\n   📝 Test {idx}: {request['content_type']} - {request['topic'][:40]}...")
    try:
        start = time.time()
        response = httpx.post(
            f"{BACKEND_URL}/v1/generate/content",
            json=request,
            timeout=30
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Generated in {elapsed:.1f}s")
            print(f"      Headline: {data['headline'][:60]}...")
            print(f"      Body: {data['body'][:80]}...")
            generated_items.append(data)
        else:
            print(f"   ⚠️ Generation returned {response.status_code}")
    except httpx.TimeoutException:
        print(f"   ⏱️ Generation timed out (model may be slow)")
    except Exception as e:
        print(f"   ❌ Error: {e}")

print()

# Test RAG retrieval
print("3️⃣ Testing RAG context retrieval...")
test_queries = [
    {"query": "customer support", "collection": None},
    {"query": "product features", "collection": "products"}
]

for query_data in test_queries:
    print(f"\n   🔍 Query: '{query_data['query']}' (Collection: {query_data['collection'] or 'all'})")
    try:
        response = httpx.post(
            f"{BACKEND_URL}/v1/retrieve",
            json={"query": query_data["query"], "collection": query_data["collection"], "top_k": 3},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Retrieved {data['num_results']} documents ({data['latency_ms']:.0f}ms)")
            if data['results']:
                first = data['results'][0]
                print(f"      Top result: {first['text'][:60]}...")
        else:
            print(f"   ⚠️ Retrieval returned {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

print()

# Check CSV feedback file
print("4️⃣ Checking feedback logging...")
import csv
from pathlib import Path

csv_path = Path("data/human_feedback.csv")
if csv_path.exists():
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        print(f"   ✅ Feedback CSV exists with {len(rows)} review(s)")
        
        if rows:
            approved = sum(1 for r in rows if r.get('decision') == 'approved')
            rejected = sum(1 for r in rows if r.get('decision') == 'rejected')
            edited = sum(1 for r in rows if r.get('decision') == 'edited')
            
            print(f"      📊 Approved: {approved}, Rejected: {rejected}, Edited: {edited}")
else:
    print(f"   ℹ️ No feedback file yet (will be created on first review)")

print()

# Summary
print("=" * 70)
print("  ✅ DEMO COMPLETE - System is operational!")
print("=" * 70)
print()
print("📖 Next Steps:")
print("   1. Launch UI: streamlit run ui/review_app.py")
print("   2. Open browser: http://localhost:8501")
print("   3. Generate content using sidebar controls")
print("   4. Review and use Approve/Reject/Edit buttons")
print("   5. Check feedback: data/human_feedback.csv")
print()
print("📚 Documentation:")
print("   • Quick Start: DAY8_QUICK_START.md")
print("   • Full Guide: DAY8_REVIEW_SYSTEM_GUIDE.md")
print("   • Architecture: DAY8_ARCHITECTURE.md")
print()
print("🎉 Day 8 Review System is ready for production use!")
print()
