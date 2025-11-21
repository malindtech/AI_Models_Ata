# API Reference
**Complete REST API Documentation**

**Base URL**: `http://localhost:8000`  
**Version**: v1  
**Framework**: FastAPI  
**Date**: November 19, 2025

---

## 📋 Table of Contents

1. [Authentication](#authentication)
2. [Content Generation Endpoints](#content-generation-endpoints)
3. [Customer Support Endpoints](#customer-support-endpoints)
4. [Retrieval Endpoints](#retrieval-endpoints)
5. [Admin Endpoints](#admin-endpoints)
6. [Error Responses](#error-responses)
7. [Rate Limits](#rate-limits)
8. [Request Examples](#request-examples)

---

## 🔐 Authentication

**Current**: No authentication (development mode)

**Production Requirements**:
- API key authentication (header: `X-API-Key`)
- JWT tokens for session-based access
- OAuth 2.0 for third-party integrations

---

## 📝 Content Generation Endpoints

### **POST** `/v1/generate/content`

Generate marketing content (blogs, products, social, emails, ads).

**Request Body**:

```json
{
  "content_type": "blog",
  "topic": "customer service automation",
  "tone": "professional",
  "additional_context": "Focus on AI chatbots",
  "customer_name": "John",
  "order_number": "ORD-12345"
}
```

| Field | Type | Required | Description | Options |
|-------|------|----------|-------------|---------|
| `content_type` | string | ✅ Yes | Type of content to generate | `blog`, `product_description`, `social_media`, `email_newsletter`, `ad_copy` |
| `topic` | string | ✅ Yes | Subject matter (1-500 chars) | Any topic string |
| `tone` | string | ✅ Yes | Writing tone | `professional`, `casual`, `technical`, `persuasive`, `educational` |
| `additional_context` | string | ❌ No | Extra instructions (max 1000 chars) | Any additional info |
| `customer_name` | string | ❌ No | Personalization token (Day 6) | Customer's name |
| `order_number` | string | ❌ No | Personalization token (Day 6) | Order/account ID |

**Response** (200 OK):

```json
{
  "content_type": "blog",
  "topic": "customer service automation",
  "tone": "professional",
  "content": {
    "headline": "Revolutionizing Customer Service with AI Automation",
    "body": "In today's fast-paced business landscape...",
    "call_to_action": "Learn more about our AI solutions"
  },
  "metadata": {
    "retrieved_examples": 5,
    "generation_time_seconds": 24.3,
    "model": "llama3:8b"
  }
}
```

**Content Structure by Type**:

| Type | Fields | Notes |
|------|--------|-------|
| `blog` | `headline`, `body`, `call_to_action` | 500-800 words |
| `product_description` | `headline`, `description`, `key_features`, `call_to_action` | Product listings |
| `social_media` | `post`, `hashtags` | Twitter/Facebook/LinkedIn |
| `email_newsletter` | `subject`, `body`, `call_to_action` | Email campaigns |
| `ad_copy` | `headline`, `body`, `call_to_action` | PPC ads |

**cURL Example**:

```bash
curl -X POST http://localhost:8000/v1/generate/content \
  -H "Content-Type: application/json" \
  -d '{
    "content_type": "blog",
    "topic": "AI in customer service",
    "tone": "professional"
  }'
```

**Python Example**:

```python
import requests

response = requests.post("http://localhost:8000/v1/generate/content", json={
    "content_type": "blog",
    "topic": "AI in customer service",
    "tone": "professional",
    "customer_name": "Sarah"
})

result = response.json()
print(result["content"]["headline"])
print(result["content"]["body"])
```

**JavaScript Example**:

```javascript
fetch('http://localhost:8000/v1/generate/content', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    content_type: 'social_media',
    topic: 'new product launch',
    tone: 'casual'
  })
})
.then(res => res.json())
.then(data => console.log(data.content.post));
```

---

### **POST** `/v1/generate/content/async`

Async version - returns job ID immediately, poll for result.

**Request Body**: Same as `/v1/generate/content`

**Response** (202 Accepted):

```json
{
  "job_id": "a3f2b9c1-4e5d-6789-abcd-ef0123456789",
  "status": "PENDING",
  "message": "Job submitted successfully"
}
```

**Poll for Result**:

```bash
GET /v1/jobs/a3f2b9c1-4e5d-6789-abcd-ef0123456789
```

**Job Status Response**:

```json
{
  "job_id": "a3f2b9c1-4e5d-6789-abcd-ef0123456789",
  "status": "SUCCESS",
  "result": {
    "content_type": "blog",
    "content": {...}
  }
}
```

| Status | Description |
|--------|-------------|
| `PENDING` | Job queued, not started |
| `STARTED` | Job in progress |
| `SUCCESS` | Job completed |
| `FAILURE` | Job failed |

---

## 💬 Customer Support Endpoints

### **POST** `/v1/support/reply`

Generate customer support reply.

**Request Body**:

```json
{
  "message": "My order hasn't arrived yet. It's been 2 weeks!",
  "intent": "complaint",
  "conversation_history": [
    {"role": "customer", "message": "I placed order #12345"},
    {"role": "agent", "message": "Let me check that for you."}
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | ✅ Yes | Customer message (1-2000 chars) |
| `intent` | string | ❌ No | Message intent (auto-detected if omitted) |
| `conversation_history` | array | ❌ No | Previous conversation turns |

**Valid Intents**: `complaint`, `inquiry`, `request`, `feedback`, `other`

**Response** (200 OK):

```json
{
  "reply": "I sincerely apologize for the delay with your order. Let me look into this immediately...",
  "detected_intent": "complaint",
  "metadata": {
    "similar_cases_retrieved": 5,
    "generation_time_seconds": 18.7,
    "extracted_info": {
      "order_numbers": ["12345"],
      "time_references": ["2 weeks"]
    }
  }
}
```

**cURL Example**:

```bash
curl -X POST http://localhost:8000/v1/support/reply \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I reset my password?",
    "intent": "inquiry"
  }'
```

**Python Example**:

```python
response = requests.post("http://localhost:8000/v1/support/reply", json={
    "message": "My order is damaged",
    "intent": "complaint"
})

print(response.json()["reply"])
```

---

### **POST** `/v1/support/classify-intent`

Classify customer message intent.

**Request Body**:

```json
{
  "message": "I want to return my purchase"
}
```

**Response** (200 OK):

```json
{
  "intent": "request",
  "confidence": 1.0,
  "all_scores": {
    "complaint": 0.0,
    "inquiry": 0.0,
    "request": 1.0,
    "feedback": 0.0,
    "other": 0.0
  }
}
```

**Intent Definitions**:

| Intent | Description | Examples |
|--------|-------------|----------|
| `complaint` | Problem/dissatisfaction | "My order is late", "Product broken" |
| `inquiry` | Question/information | "What are your hours?", "How do I..." |
| `request` | Action needed | "Cancel my order", "Send invoice" |
| `feedback` | Praise/suggestion | "Great service!", "You should add..." |
| `other` | Unclear/mixed | Ambiguous messages |

**Accuracy**: 100% on curated test set (Day 5)

---

### **POST** `/v1/support/reply/async`

Async version - returns job ID, poll for result.

**Request Body**: Same as `/v1/support/reply`

**Response**: Same async pattern as content generation

---

## 🔍 Retrieval Endpoints

### **POST** `/v1/retrieve`

Retrieve similar documents from vector database.

**Request Body**:

```json
{
  "query": "customer service best practices",
  "collections": ["blogs", "support"],
  "top_k": 5,
  "enable_expansion": true
}
```

| Field | Type | Required | Description | Default |
|-------|------|----------|-------------|---------|
| `query` | string | ✅ Yes | Search query (1-500 chars) | - |
| `collections` | array | ✅ Yes | Collections to search | - |
| `top_k` | integer | ❌ No | Number of results per collection | 5 |
| `enable_expansion` | boolean | ❌ No | Use query expansion (Day 6) | true |

**Valid Collections**: `blogs`, `products`, `support`, `social`, `reviews`

**Response** (200 OK):

```json
{
  "query": "customer service best practices",
  "expanded_queries": [
    "customer service best practices",
    "customer support best practices",
    "customer experience best practices"
  ],
  "results": [
    {
      "id": "blog_042",
      "text": "Building exceptional customer service requires...",
      "metadata": {
        "source": "blogs",
        "title": "Customer Service Excellence",
        "date": "2024-03-15"
      },
      "similarity": 0.87
    }
  ],
  "total_results": 10,
  "retrieval_time_seconds": 0.15
}
```

**cURL Example**:

```bash
curl -X POST http://localhost:8000/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "shipping delays",
    "collections": ["support"],
    "top_k": 3
  }'
```

**Python Example**:

```python
response = requests.post("http://localhost:8000/v1/retrieve", json={
    "query": "product recommendations",
    "collections": ["products", "reviews"],
    "top_k": 10,
    "enable_expansion": True
})

for result in response.json()["results"]:
    print(f"• {result['metadata']['title']} (similarity: {result['similarity']:.2f})")
```

---

## ⚙️ Admin Endpoints

### **GET** `/v1/health`

Health check endpoint.

**Response** (200 OK):

```json
{
  "status": "healthy",
  "timestamp": "2025-11-19T16:30:00Z",
  "version": "1.0.0",
  "services": {
    "fastapi": "running",
    "ollama": "running",
    "chromadb": "running"
  }
}
```

---

### **GET** `/v1/stats`

Get system statistics.

**Response** (200 OK):

```json
{
  "collections": {
    "blogs": 243,
    "products": 197,
    "support": 272,
    "social": 177,
    "reviews": 196
  },
  "total_documents": 1085,
  "model": "llama3:8b",
  "embedding_model": "all-MiniLM-L6-v2"
}
```

---

### **POST** `/v1/admin/add-document`

Add document to vector database (admin only).

**Request Body**:

```json
{
  "collection": "blogs",
  "text": "This is a new blog post about AI...",
  "metadata": {
    "title": "New Blog Post",
    "author": "John Doe",
    "date": "2025-11-19"
  }
}
```

**Response** (201 Created):

```json
{
  "id": "blog_1086",
  "collection": "blogs",
  "message": "Document added successfully"
}
```

---

### **DELETE** `/v1/admin/delete-document`

Delete document from vector database (admin only).

**Request Body**:

```json
{
  "collection": "blogs",
  "document_id": "blog_1086"
}
```

**Response** (200 OK):

```json
{
  "message": "Document deleted successfully",
  "collection": "blogs",
  "document_id": "blog_1086"
}
```

---

## ❌ Error Responses

### **Error Schema**:

```json
{
  "error": "ValidationError",
  "message": "Invalid content_type. Must be one of: blog, product_description, social_media, email_newsletter, ad_copy",
  "details": {
    "field": "content_type",
    "provided_value": "invalid_type"
  },
  "timestamp": "2025-11-19T16:30:00Z"
}
```

### **HTTP Status Codes**:

| Code | Error Type | Description |
|------|------------|-------------|
| **400** | Bad Request | Invalid input (missing required fields, validation errors) |
| **422** | Unprocessable Entity | Pydantic validation failed |
| **500** | Internal Server Error | Server-side error (LLM failure, DB error) |
| **503** | Service Unavailable | Ollama not running, ChromaDB unavailable |

### **Common Errors**:

**Missing Required Field**:
```json
{
  "error": "ValidationError",
  "message": "Field 'topic' is required",
  "details": {"field": "topic"}
}
```

**Invalid Enum Value**:
```json
{
  "error": "ValidationError",
  "message": "Invalid tone. Must be one of: professional, casual, technical, persuasive, educational",
  "details": {"field": "tone", "provided_value": "friendly"}
}
```

**LLM Generation Failed**:
```json
{
  "error": "GenerationError",
  "message": "Failed to generate content: Ollama connection refused",
  "details": {"service": "ollama", "url": "http://localhost:11434"}
}
```

**Rate Limit Exceeded** (if implemented):
```json
{
  "error": "RateLimitError",
  "message": "Rate limit exceeded: 100 requests per hour",
  "details": {"retry_after": 3600}
}
```

---

## 🚦 Rate Limits

**Current**: No rate limits (development mode)

**Recommended Production Limits**:
- **Free Tier**: 100 requests/hour per IP
- **Paid Tier**: 1,000 requests/hour per API key
- **Enterprise**: Unlimited

**Headers** (when implemented):
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1700409600
```

---

## 📚 Request Examples

### **Example 1: Blog Generation with Personalization**

```python
import requests

response = requests.post("http://localhost:8000/v1/generate/content", json={
    "content_type": "blog",
    "topic": "benefits of cloud computing",
    "tone": "professional",
    "additional_context": "Focus on cost savings for SMBs",
    "customer_name": "Sarah"
})

blog = response.json()
print(f"Headline: {blog['content']['headline']}")
print(f"Body: {blog['content']['body'][:200]}...")
print(f"Generation time: {blog['metadata']['generation_time_seconds']:.1f}s")
```

### **Example 2: Support Reply with Context**

```python
response = requests.post("http://localhost:8000/v1/support/reply", json={
    "message": "I haven't received my refund yet",
    "intent": "complaint",
    "conversation_history": [
        {"role": "customer", "message": "I returned my order last week"},
        {"role": "agent", "message": "Refunds take 5-7 business days"}
    ]
})

print(response.json()["reply"])
```

### **Example 3: Batch Content Generation**

```python
from concurrent.futures import ThreadPoolExecutor
import requests

topics = [
    "AI in healthcare",
    "Cloud security best practices",
    "Remote work productivity",
    "Sustainable packaging"
]

def generate(topic):
    response = requests.post("http://localhost:8000/v1/generate/content", json={
        "content_type": "blog",
        "topic": topic,
        "tone": "professional"
    })
    return response.json()

# Generate in parallel (4 concurrent requests)
with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(generate, topics))

for i, result in enumerate(results):
    print(f"{i+1}. {result['content']['headline']}")
```

### **Example 4: Retrieve + Generate Pipeline**

```python
# Step 1: Retrieve relevant examples
retrieval = requests.post("http://localhost:8000/v1/retrieve", json={
    "query": "customer retention strategies",
    "collections": ["blogs", "products"],
    "top_k": 3
}).json()

# Step 2: Use retrieved context for generation
context = "\n".join([r["text"][:200] for r in retrieval["results"]])

generation = requests.post("http://localhost:8000/v1/generate/content", json={
    "content_type": "email_newsletter",
    "topic": "customer retention strategies",
    "tone": "professional",
    "additional_context": f"Use these examples:\n{context}"
}).json()

print(generation["content"]["subject"])
print(generation["content"]["body"])
```

### **Example 5: Intent Classification for Routing**

```python
def route_message(message: str):
    """Route customer message based on intent"""
    
    # Classify intent
    intent = requests.post("http://localhost:8000/v1/support/classify-intent", json={
        "message": message
    }).json()
    
    # Route based on intent
    if intent["intent"] == "complaint":
        print("→ Route to senior agent")
    elif intent["intent"] == "inquiry":
        print("→ Route to knowledge base")
    elif intent["intent"] == "request":
        print("→ Route to action queue")
    else:
        print("→ Route to general support")
    
    return intent

# Test
route_message("My order is damaged")  # → senior agent
route_message("What are your hours?")  # → knowledge base
route_message("Please cancel my subscription")  # → action queue
```

---

## 🔗 OpenAPI Specification

**Swagger UI**: `http://localhost:8000/docs`  
**ReDoc**: `http://localhost:8000/redoc`  
**OpenAPI JSON**: `http://localhost:8000/openapi.json`

---

## 📞 Support

**Documentation**: `docs/`  
**GitHub Issues**: Not configured  
**Email**: Not configured

---

**Last Updated**: November 19, 2025  
**Version**: 1.0  
**Status**: ✅ Complete
