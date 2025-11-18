# Day 6 - Quick Reference Guide

## Query Expansion

### What It Does
Automatically generates query variations to improve retrieval quality.

### Example
```python
from backend.rag_utils import expand_query

query = "My laptop won't turn on"
variations = expand_query(query, num_variations=3)
# Returns: [
#   "My laptop won't turn on",           # Original
#   "computer power issue",              # Generalized
#   "device unable to start"             # Simplified
# ]
```

### Using with Retrieval
```python
from backend.rag_utils import retrieve_with_expanded_queries

results = retrieve_with_expanded_queries(
    collection_name="support",
    query="My order hasn't arrived",
    client=chroma_client,
    k=5,
    num_query_variations=2  # Try 2 variations
)
# Returns: Deduped results ranked by relevance
```

---

## Personalization

### Simple Personalization
```python
from backend.rag_utils import personalize_response

template = "Hello {customer_name}, how can we help you today?"
result = personalize_response(
    template,
    customer_name="Sarah Johnson"
)
# Result: "Hello Sarah Johnson, how can we help you today?"
```

### With First Name Extraction
```python
template = "Hi {first_name}, we've received your inquiry!"
result = personalize_response(
    template,
    customer_name="John Smith"
)
# Result: "Hi John, we've received your inquiry!"
```

### Full Personalization
```python
result = personalize_response(
    "Hi {first_name}, your ticket #{customer_id} has been received.",
    customer_name="Jane Doe",
    customer_id="CUST-12345"
)
# Result: "Hi Jane, your ticket #CUST-12345 has been received."
```

---

## API Usage

### New Async Endpoint with All Features

```bash
curl -X POST http://localhost:8000/generate-reply-async \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need help with my order",
    "customer_name": "John Smith",
    "k": 5,
    "max_validation_retries": 2
  }'
```

### Python Example
```python
import requests

# Submit task
payload = {
    "message": "My product arrived damaged",
    "customer_name": "Sarah Johnson",
    "k": 5,  # Retrieve top-5 contexts
    "max_validation_retries": 1
}

response = requests.post(
    "http://localhost:8000/generate-reply-async",
    json=payload
)

task_id = response.json()["task_id"]
print(f"Task ID: {task_id}")

# Poll for result
import time
max_polls = 30

for i in range(max_polls):
    time.sleep(0.5)
    
    status_response = requests.get(
        f"http://localhost:8000/task-status/{task_id}"
    )
    
    status_data = status_response.json()
    
    if status_data["status"] == "success":
        result = status_data["result"]
        print(f"Reply: {result['reply']}")
        print(f"Intent: {result['detected_intent']}")
        print(f"Next Steps: {result['next_steps']}")
        break
    elif status_data["status"] == "failed":
        print(f"Error: {status_data['error']}")
        break
    else:
        print(f"Status: {status_data['status']}...")
```

---

## K-Value Configuration

### What is K?
K is the number of similar documents to retrieve from the vector database.

### Recommended Values

| K Value | Use Case | Speed | Quality |
|---------|----------|-------|---------|
| 3 | Quick responses | ⚡⚡⚡ | ⭐⭐⭐ |
| 5 | **Default (balanced)** | ⚡⚡ | ⭐⭐⭐⭐ |
| 7 | Comprehensive | ⚡ | ⭐⭐⭐⭐⭐ |
| 10 | Maximum accuracy | - | ⭐⭐⭐⭐⭐ |

### API Parameter
```json
{
  "message": "customer message",
  "k": 5  // Change this value
}
```

---

## Testing Scripts

### Run K-Value Tests
```bash
python scripts/test_k_values.py
```

**Tests**:
- K values: 3, 5, 7, 10
- 10 different customer messages
- Success rate and latency metrics
- Personalization compatibility

**Output**: `logs/day6_k_value_test_*.json`

### Run Large Dataset Tests
```bash
python scripts/test_large_dataset_day6.py
```

**Tests**:
- 100 document samples (adjustable)
- Scenario 1: Without personalization
- Scenario 2: With personalization
- K-value comparison (3, 5, 7, 10)

**Output**: `logs/day6_large_dataset_test_*.json`

---

## Response Examples

### With Personalization
```json
{
  "status": "success",
  "result": {
    "message": "I need help with my order",
    "detected_intent": "inquiry",
    "reply": "Hi Sarah, thank you for contacting us about your order. We're here to help...",
    "next_steps": "Please provide your order number so we can look into this for you.",
    "total_latency_s": 2.5
  }
}
```

### Without Personalization
```json
{
  "status": "success",
  "result": {
    "message": "I need help with my order",
    "detected_intent": "inquiry",
    "reply": "Thank you for contacting us about your order. We're here to help...",
    "next_steps": "Please provide your order number so we can look into this for you.",
    "total_latency_s": 2.3
  }
}
```

---

## Logging & Debugging

### View RAG Context Injection
```python
from loguru import logger
logger.enable("backend.rag_utils")
```

### Check Query Expansion Details
```
2025-11-14 15:30:45.123 | INFO | Generated 3 query variations
2025-11-14 15:30:45.456 | INFO | Query expansion: 3 variations -> 5 unique results
```

### Monitor Personalization
```
2025-11-14 15:30:46.789 | DEBUG | Personalized prompt with customer name: John Smith
2025-11-14 15:30:46.890 | DEBUG | Personalized response with customer name: John Smith
```

---

## Performance Tips

### For Fast Responses
```python
{
  "message": "customer message",
  "customer_name": "Name",
  "k": 3  # Faster
}
```

### For Better Quality
```python
{
  "message": "customer message",
  "customer_name": "Name",
  "k": 7  # Better quality
}
```

### For Balanced Performance
```python
{
  "message": "customer message",
  "customer_name": "Name",
  "k": 5  # Recommended default
}
```

---

## Troubleshooting

### Query Expansion Not Working
**Check**: ChromaDB is initialized and has data
```bash
curl http://localhost:8000/health
# Should return: {"status": "ok", "vector_db": true}
```

### Personalization Not Applied
**Check**: Customer name is provided and not None
```python
# ❌ Wrong
payload = {
  "message": "help",
  "customer_name": None  # Will be ignored
}

# ✅ Correct
payload = {
  "message": "help",
  "customer_name": "John Smith"  # Will be personalized
}
```

### K-Value Not Affecting Results
**Check**: Vector DB has sufficient data (100+ documents per collection)
```bash
# Initialize vector DB
python scripts/initialize_vectordb.py
```

---

## Next Steps

1. **Run Tests**: Execute both test scripts to validate performance
2. **Analyze Results**: Review JSON output for metrics
3. **Optimize**: Select best k-value for your use case
4. **Deploy**: Update production with optimized values
5. **Monitor**: Track personalization effectiveness

---

## Additional Resources

- **Full Summary**: See `DAY6_SUMMARY.md`
- **Celery Tasks**: `backend/celery_tasks.py`
- **RAG Utils**: `backend/rag_utils.py`
- **Main API**: `backend/main.py`
- **Tests**: `scripts/test_*.py`
