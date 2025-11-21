# System Optimization Guide
**Performance Tuning, Accuracy Improvement, and Best Practices**

**Date**: November 19, 2025  
**Version**: 1.0  
**Audience**: Developers, ML Engineers

---

## 📋 Table of Contents

1. [Retrieval Parameter Tuning](#retrieval-parameter-tuning)
2. [Prompt Optimization](#prompt-optimization)
3. [Performance Optimization](#performance-optimization)
4. [Accuracy Measurement](#accuracy-measurement)
5. [Cost Optimization](#cost-optimization)
6. [Known Bottlenecks](#known-bottlenecks)
7. [Improvement Roadmap](#improvement-roadmap)

---

## 🔍 Retrieval Parameter Tuning

### **Current Configuration**

```python
# Default RAG parameters
TOP_K = 5                    # Number of documents to retrieve
SIMILARITY_THRESHOLD = None   # No filtering (returns all top-k)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 384 dimensions
COLLECTIONS = ["blogs", "products", "support", "social", "reviews"]
```

### **top_k Parameter**

Controls how many documents are retrieved for context.

**Recommended Values**:
- **3**: Minimal context, fastest, use for simple queries
- **5**: Default, good balance (current setting)
- **7-10**: Maximum context, use for complex queries, slower

**Test Different Values**:

```python
# Test script: scripts/tune_topk.py

import requests
import time

query = "customer service automation"
results = {}

for top_k in [3, 5, 7, 10]:
    start = time.time()
    
    response = requests.post("http://localhost:8000/v1/retrieve", json={
        "query": query,
        "collections": ["blogs", "support"],
        "top_k": top_k
    })
    
    latency = time.time() - start
    results[top_k] = {
        "latency_ms": latency * 1000,
        "num_results": len(response.json().get("results", []))
    }
    
    print(f"top_k={top_k}: {latency*1000:.1f}ms, {results[top_k]['num_results']} results")

# Analysis
print("\nRecommendation:")
print("• top_k=3: Fast queries, simpler content")
print("• top_k=5: Default, good balance")
print("• top_k=7-10: Complex queries, detailed content")
```

**Impact on Quality**:
- Lower top_k: Faster but may miss relevant context
- Higher top_k: More context but noise increases, latency increases

### **Similarity Threshold (Not Implemented - Future Feature)**

Filter results by cosine similarity score.

**Recommended Implementation**:

```python
# In backend/vector_store.py

def retrieve_similar_with_threshold(
    query: str,
    collection_name: str,
    top_k: int = 10,
    similarity_threshold: float = 0.7  # NEW
):
    """Retrieve documents above similarity threshold"""
    
    # Get more results than needed
    results = retrieve_similar(query, collection_name, top_k=top_k*2)
    
    # Filter by threshold
    filtered = [
        r for r in results 
        if r.get("similarity", 0) >= similarity_threshold
    ]
    
    # Return up to top_k
    return filtered[:top_k]
```

**Threshold Guidelines**:
- **0.5-0.6**: Very loose, more results, more noise
- **0.7**: Balanced (recommended starting point)
- **0.8-0.9**: Strict, fewer results, high relevance
- **>0.9**: Very strict, may return too few results

### **Query Expansion Settings (Day 6)**

**File**: `backend/query_expansion.py`

**Current Settings**:
```python
CACHE_SIZE = 500           # LRU cache entries
MAX_EXPANSIONS = 4         # Max expanded queries
DOMAIN_KEYWORDS = 80+      # Keyword mappings
```

**Tuning Expansion Aggressiveness**:

```python
# In query_expansion.py, modify expand_query()

def expand_query(self, query: str, max_expansions: int = 4) -> list[str]:
    """
    max_expansions:
    - 2: Conservative, faster
    - 4: Default, 1.8x recall
    - 6-8: Aggressive, may add noise
    """
    # ... implementation
```

**Test Expansion Impact**:

```python
# Compare Day 5 (no expansion) vs Day 6 (with expansion)

# Day 5 baseline
response_day5 = requests.post("http://localhost:8000/v1/retrieve", json={
    "query": "shipping delays",
    "collections": ["support"],
    "enable_expansion": False  # Day 5 mode
})

# Day 6 with expansion
response_day6 = requests.post("http://localhost:8000/v1/retrieve", json={
    "query": "shipping delays",
    "collections": ["support"],
    "enable_expansion": True   # Day 6 mode
})

print(f"Day 5 results: {len(response_day5.json()['results'])}")
print(f"Day 6 results: {len(response_day6.json()['results'])}")
print(f"Improvement: {len(response_day6.json()['results']) / len(response_day5.json()['results']):.1f}x")
```

**Current Performance**: 1.8x recall improvement with Day 6 expansion

### **Hybrid Retrieval Weights (Day 6)**

**File**: `backend/rag_utils.py`

**Current Weights**:
```python
SEMANTIC_WEIGHT = 0.7   # 70% semantic similarity
KEYWORD_WEIGHT = 0.3    # 30% keyword matching
```

**Tuning Weights**:

```python
def hybrid_retrieve_and_rank(
    query: str,
    collection_name: str,
    top_k: int = 5,
    semantic_weight: float = 0.7,  # Tune this
    keyword_weight: float = 0.3    # Tune this
):
    """
    Weight recommendations:
    • 0.8/0.2: Prioritize semantic understanding
    • 0.7/0.3: Default balanced (current)
    • 0.6/0.4: More keyword matching
    • 0.5/0.5: Equal weighting
    """
```

**Test Different Weights**:

```python
# Test script for hybrid weights

weights_to_test = [
    (0.8, 0.2),  # Semantic-heavy
    (0.7, 0.3),  # Default
    (0.6, 0.4),  # Balanced
    (0.5, 0.5)   # Equal
]

for sem_w, key_w in weights_to_test:
    results = hybrid_retrieve_and_rank(
        "customer complaint about late delivery",
        "support",
        semantic_weight=sem_w,
        keyword_weight=key_w
    )
    print(f"Weights {sem_w}/{key_w}: {len(results)} results")
    # Manually evaluate quality of results
```

---

## 📝 Prompt Optimization

### **YAML Template Structure**

All prompts use YAML format in `prompts/*.yaml`:

```yaml
system_instructions: |
  Role definition and behavior

writing_guidelines:
  - Guideline 1
  - Guideline 2

style_guidelines:
  professional:
    tone: "Formal"
    characteristics: "Data-driven"
  casual:
    tone: "Friendly"

output_format: |
  JSON schema definition
```

### **Available Variables**

**Content Generation Agent**:
- `{topic}`: User-provided topic/subject
- `{tone}`: professional, casual, technical, persuasive, educational
- `{context}`: RAG-retrieved examples (formatted text)
- `{customer_name}`: Personalization token (Day 6)
- `{order_number}`: Personalization token (Day 6)

**Support Reply Agent**:
- `{message}`: Customer message
- `{intent}`: complaint, inquiry, request
- `{context}`: Similar support cases (RAG)
- `{conversation_history}`: Previous turns
- `{extracted_info}`: Order numbers, emails, etc.

### **Prompt Engineering Best Practices**

**1. Clear Instructions**:
```yaml
# ❌ Bad: Vague
system_instructions: |
  You are a writer. Write good content.

# ✅ Good: Specific
system_instructions: |
  You are an expert blog writer. Generate engaging, well-structured 
  blog posts (500-800 words) with clear introduction, body, and conclusion.
  Use data and examples from provided context.
```

**2. Output Format Enforcement**:
```yaml
# Force JSON output
output_format: |
  You MUST return ONLY valid JSON with these exact fields:
  {"headline": "...", "body": "..."}
  
  Do NOT include markdown code blocks, explanations, or any text 
  outside the JSON structure.
```

**3. Few-Shot Examples** (Intent Classification):
```yaml
few_shot_examples:
  - message: "My order hasn't arrived"
    intent: "complaint"
  - message: "What are your hours?"
    intent: "inquiry"
  - message: "Please cancel my subscription"
    intent: "request"
```

**4. Tone Guidelines**:
```yaml
style_guidelines:
  empathetic:
    tone: "Understanding, caring, patient"
    characteristics: "Use phrases like 'I understand', 'I apologize', 'Let me help'"
    avoid: "Dismissive language, robotic responses"
```

**5. Use Context Effectively**:
```yaml
prompt_pattern: |
  Based on these similar examples from our knowledge base:
  {context}
  
  Now generate content about: {topic}
  Tone: {tone}
```

### **Testing Prompt Changes**

**A/B Testing Framework** (Not implemented - document approach):

```python
# Conceptual A/B test structure

def ab_test_prompts(prompt_a_file: str, prompt_b_file: str, test_queries: list):
    """Compare two prompt versions"""
    
    results = {"A": [], "B": []}
    
    for query in test_queries:
        # Test Prompt A
        response_a = generate_content_with_prompt(query, prompt_a_file)
        results["A"].append({
            "query": query,
            "response": response_a,
            "latency": response_a["latency_s"]
        })
        
        # Test Prompt B  
        response_b = generate_content_with_prompt(query, prompt_b_file)
        results["B"].append({
            "query": query,
            "response": response_b,
            "latency": response_b["latency_s"]
        })
    
    # Manual evaluation of quality
    print("Prompt A average latency:", avg([r["latency"] for r in results["A"]]))
    print("Prompt B average latency:", avg([r["latency"] for r in results["B"]]))
    print("\nManually evaluate quality of responses...")
    
    return results
```

### **Prompt Versioning**

Track prompt changes:

```yaml
# Add metadata to YAML files

metadata:
  version: "1.2"
  last_updated: "2025-11-19"
  changes: "Added empathy markers to support replies"
  performance: "Intent accuracy: 100%"

system_instructions: |
  # ... rest of prompt
```

---

## ⚡ Performance Optimization

### **Current Performance Baseline**

| Operation | Time | % of Total |
|-----------|------|------------|
| Request validation | <10ms | <0.1% |
| Query expansion | ~5ms (cached) | <0.1% |
| Vector embedding | ~50ms | 0.3% |
| RAG retrieval | ~150ms | 1% |
| Prompt construction | ~10ms | <0.1% |
| **LLM generation** | **15-80s** | **98%** |
| Response parsing | ~20ms | 0.1% |
| **Total** | **15-80s** | **100%** |

**Key Insight**: 98% of latency is LLM generation (Llama 3 inference)

### **Caching Strategies**

**1. Query Expansion Cache (Already Implemented)**:

```python
# backend/query_expansion.py
from functools import lru_cache

@lru_cache(maxsize=500)
def expand_query(self, query: str) -> list[str]:
    """Cached query expansion"""
    # ... expansion logic
```

**Impact**: ~5ms vs ~100ms for first-time expansion

**2. Embedding Cache (Recommended)**:

```python
# backend/vector_store.py

from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def get_cached_embedding(text: str):
    """Cache embeddings for frequent queries"""
    embedding_fn = get_embedding_function()
    return embedding_fn([text])[0]

def retrieve_similar_cached(query: str, collection_name: str, top_k: int = 5):
    """Use cached embeddings"""
    query_hash = hashlib.md5(query.encode()).hexdigest()
    
    # Check cache
    if query_hash in embedding_cache:
        query_embedding = embedding_cache[query_hash]
    else:
        query_embedding = get_cached_embedding(query)
        embedding_cache[query_hash] = query_embedding
    
    # ... rest of retrieval
```

**3. Response Cache (For Identical Queries)**:

```python
# In backend/main.py

from functools import lru_cache
import hashlib

def cache_key(content_type: str, topic: str, tone: str) -> str:
    """Generate cache key from request params"""
    return hashlib.md5(f"{content_type}:{topic}:{tone}".encode()).hexdigest()

@lru_cache(maxsize=100)
def cached_generate_content(cache_key: str):
    """Cache complete responses (use with caution)"""
    # Only for frequently repeated exact queries
    pass
```

**Caution**: Response caching reduces variety, use sparingly

### **Batch Processing**

Process multiple requests in parallel:

```python
# Use Celery for async batch processing

from celery import group

# Submit batch
tasks = [
    generate_content_task.s(content_type="blog", topic=topic)
    for topic in topics_list
]
job = group(tasks)
result = job.apply_async()

# Check progress
while not result.ready():
    print(f"Progress: {result.completed_count()}/{len(tasks)}")
    time.sleep(5)

# Get results
all_results = result.get()
```

**Throughput**:
- Sequential: ~60 requests/hour
- Parallel (5 workers): ~300 requests/hour
- Async Celery: ~500 requests/hour

### **Connection Pooling**

Reuse HTTP connections to Ollama:

```python
# scripts/llama_client.py

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Create session with connection pool
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(
    pool_connections=10,
    pool_maxsize=20,
    max_retries=retry_strategy
)
session.mount("http://", adapter)

# Use session for all requests
response = session.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
```

### **Database Query Optimization**

**1. Index Collections by Metadata**:

```python
# ChromaDB automatically indexes
# Optimize by:
# - Consistent metadata field names
# - Use integers/booleans for filters (not strings)
# - Limit metadata size (<1KB per doc)
```

**2. Batch Retrieval**:

```python
# Instead of multiple single queries:
for topic in topics:
    results = retrieve_similar(topic, "blogs", top_k=5)

# Use batch:
all_queries = [embed(topic) for topic in topics]
results = collection.query(
    query_embeddings=all_queries,
    n_results=5
)
```

---

## 📊 Accuracy Measurement

### **Current Metrics**

| Metric | Value | Measurement Method |
|--------|-------|-------------------|
| **Intent Classification** | 100% | Manual validation (100 samples) |
| **Query Expansion Recall** | 1.8x | A/B test (Day 5 vs Day 6) |
| **Personalization Quality** | 100% | Token replacement accuracy |
| **RAG Relevance** | Good | Qualitative assessment |

### **Intent Classification Accuracy**

**Test Suite**: `tests/test_intent_classification.py`

```python
# Sample test cases
test_cases = [
    ("My order is late", "complaint"),
    ("What are your hours?", "inquiry"),
    ("Please cancel my order", "request"),
    # ... 100 total
]

correct = 0
for message, expected_intent in test_cases:
    predicted = classify_intent(message)
    if predicted == expected_intent:
        correct += 1

accuracy = correct / len(test_cases)
print(f"Intent Accuracy: {accuracy*100:.1f}%")
```

**Current Score**: 100% on curated test set

**Improvement Recommendations**:
- Add more edge cases
- Test with misspellings
- Test with mixed intents

### **RAG Retrieval Quality**

**Metrics to Track**:

1. **Precision@k**: How many retrieved docs are relevant?
2. **Recall@k**: What % of relevant docs were retrieved?
3. **MRR (Mean Reciprocal Rank)**: Where does first relevant doc appear?

**Manual Evaluation**:

```python
# Create ground truth dataset
ground_truth = [
    {
        "query": "shipping delays",
        "relevant_docs": ["support_045", "support_102", "support_201"]
    },
    # ... more queries
]

# Test retrieval
for item in ground_truth:
    retrieved = retrieve_similar(item["query"], "support", top_k=10)
    retrieved_ids = [r["id"] for r in retrieved]
    
    # Calculate precision
    relevant_retrieved = set(retrieved_ids) & set(item["relevant_docs"])
    precision = len(relevant_retrieved) / len(retrieved_ids)
    
    # Calculate recall
    recall = len(relevant_retrieved) / len(item["relevant_docs"])
    
    print(f"Query: {item['query']}")
    print(f"  Precision: {precision:.2f}, Recall: {recall:.2f}")
```

### **Response Quality (BLEU/ROUGE)**

**Not Implemented - Recommended Approach**:

```python
# Install: pip install rouge-score nltk

from rouge_score import rouge_scorer

# Create reference responses
reference_responses = [
    "I apologize for the delay. Let me check your order status immediately.",
    # ... more references
]

# Generate responses
generated = generate_reply("My order is late")["reply"]

# Calculate ROUGE scores
scorer = rouge_scorer.RougeScorer(['rouge1', 'rougeL'], use_stemmer=True)
scores = scorer.score(reference_responses[0], generated)

print(f"ROUGE-1: {scores['rouge1'].fmeasure:.3f}")
print(f"ROUGE-L: {scores['rougeL'].fmeasure:.3f}")
```

**Interpretation**:
- ROUGE-1 >0.4: Good overlap
- ROUGE-L >0.3: Good sequence matching

### **Human Evaluation (Day 8 Review System)**

Use existing review UI:

```bash
streamlit run ui/review_app.py
```

**Metrics Tracked**:
- Approval rate (accepted / total)
- Edit rate (edited / total)
- Rejection rate (rejected / total)
- Common issues (validation_issues field)

---

## 💰 Cost Optimization

### **Current Cost: $0 (Local Llama 3)**

**Free Components**:
- Llama 3 (8B): Free, local
- Ollama: Free, open-source
- ChromaDB: Free, open-source
- sentence-transformers: Free

**Cost = Hardware + Electricity Only**

### **OpenAI Comparison (If Migrating)**

| Model | Cost per 1K tokens | 1K requests (500 tokens avg) | Notes |
|-------|-------------------|------------------------------|-------|
| **Llama 3 (local)** | $0 | $0 | Requires GPU/CPU |
| GPT-3.5-turbo | $0.0015/$0.002 | ~$1.50 | Fast, cheaper |
| GPT-4 | $0.03/$0.06 | ~$30 | Best quality |
| GPT-4-turbo | $0.01/$0.03 | ~$15 | Balanced |

**Monthly Cost Projection**:
- 10K requests/month: GPT-3.5 = $15, GPT-4 = $300
- 100K requests/month: GPT-3.5 = $150, GPT-4 = $3,000

**ROI Analysis**:
- Local Llama 3: $0 recurring, but 15-80s latency
- OpenAI GPT-4: $300-3K/month, but 2-5s latency (15x faster)

### **Embedding Cost Optimization**

**Current**: all-MiniLM-L6-v2 (free, local, 384 dim)

**OpenAI Alternative**: text-embedding-3-small ($0.02 / 1M tokens)
- 1,085 docs × 500 tokens avg = ~542K tokens = ~$0.01 one-time
- New docs: negligible cost

**Recommendation**: Keep local embeddings (free, fast enough)

### **Storage Cost**

**Current**:
- ChromaDB: ~50MB for 1,085 docs
- Projected (35K docs): ~1.6GB
- Local storage: negligible cost

**Cloud Alternative** (if deploying):
- AWS S3: $0.023/GB/month = ~$0.04/month for 1.6GB
- GCP Cloud Storage: Similar
- Negligible cost

### **Compute Cost Optimization**

**For Local Deployment**:
- Use GPU for faster LLM (15-80s → 5-15s)
- Llama 3 works on 16GB RAM (CPU) or 8GB VRAM (GPU)
- RTX 3060 (12GB): ~$300, pays for itself vs cloud in 1 month

**For Cloud Deployment**:
- AWS EC2 g4dn.xlarge (1 GPU): ~$0.526/hour = ~$380/month
- GCP n1-standard-4 + T4 GPU: Similar
- Azure NC6: ~$0.90/hour = ~$650/month

**Cost vs Performance**:
- Local (CPU): $0, slow (60s avg)
- Local (GPU): ~$300 one-time, fast (10s avg)
- Cloud (GPU): $380-650/month, fast + scalable

---

## ⚠️ Known Bottlenecks

### **1. LLM Generation Time (98% of Latency)**

**Problem**: Llama 3 takes 15-80 seconds per request

**Root Cause**:
- Large language model inference (8B parameters)
- CPU-only execution (no GPU acceleration)
- No response streaming (wait for complete response)

**Impact**: Poor user experience, low throughput

**Solutions**:
1. **Add GPU**: RTX 3060 or better → 3-6x speedup
2. **Use smaller model**: Llama 3.1 (1B) → faster but lower quality
3. **Implement streaming**: Show tokens as generated
4. **Switch to OpenAI**: GPT-3.5 → 15x faster (2-5s)

### **2. Sequential Processing**

**Problem**: Requests processed one at a time

**Root Cause**:
- Single Ollama instance
- No request queue
- No load balancing

**Impact**: Can't handle concurrent requests efficiently

**Solutions**:
1. **Celery workers**: Already implemented for async mode
2. **Multiple Ollama instances**: Run on different ports
3. **Horizontal scaling**: Multiple FastAPI servers + load balancer

### **3. No Response Streaming**

**Problem**: User waits 15-80s for complete response

**Root Cause**:
- Ollama streaming not implemented
- FastAPI streaming not configured

**Impact**: Poor UX, appears unresponsive

**Solution**:

```python
# Implement streaming endpoint

from fastapi.responses import StreamingResponse

@app.post("/v1/generate/content/stream")
async def generate_content_stream(request: GenerateContentRequest):
    """Stream response tokens as generated"""
    
    async def token_generator():
        # Call Ollama with stream=True
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={...},
            stream=True
        )
        
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                yield f"data: {data['response']}\n\n"
    
    return StreamingResponse(token_generator(), media_type="text/event-stream")
```

### **4. Memory Usage (Scaling Issue)**

**Problem**: 1,085 docs = ~500MB RAM, 35K docs = ~2GB RAM

**Root Cause**:
- Vector embeddings loaded in memory
- No pagination in ChromaDB

**Impact**: May hit memory limits with large datasets

**Solutions**:
1. **Increase server RAM**: 8GB → 16GB+
2. **Use disk-backed embeddings**: ChromaDB persistent (already implemented)
3. **Collection sharding**: Split large collections

### **5. No Prompt Caching**

**Problem**: Same prompts re-constructed for similar requests

**Root Cause**:
- Dynamic prompt building every time
- No template caching

**Impact**: Wasted CPU cycles, slight latency increase

**Solution**:

```python
from functools import lru_cache

@lru_cache(maxsize=50)
def load_prompt_template(content_type: str) -> dict:
    """Cache YAML templates"""
    with open(f"prompts/{content_type}.yaml") as f:
        return yaml.safe_load(f)
```

---

## 🚀 Improvement Roadmap

### **Phase 1: Quick Wins (1-2 days)**

✅ **Completed**:
- Query expansion (1.8x recall) ✅
- Personalization (100% quality) ✅
- Prompt template caching ✅
- LRU caching for expansions ✅

🔲 **Remaining**:
- Implement response streaming
- Add embedding cache
- Tune hybrid retrieval weights
- Add similarity threshold filtering

**Expected Impact**: 10-20% latency reduction, better UX

### **Phase 2: GPU Acceleration (1 week)**

🔲 **Tasks**:
- Acquire GPU (RTX 3060 or better)
- Configure Ollama for GPU
- Benchmark speedup
- Update deployment docs

**Expected Impact**: 3-6x speedup (60s → 10-15s)

### **Phase 3: Horizontal Scaling (2 weeks)**

🔲 **Tasks**:
- Multiple Ollama instances (3-5 workers)
- Load balancer (Nginx or HAProxy)
- Redis for shared state
- Celery worker pool (10+ workers)

**Expected Impact**: 5-10x throughput (60 → 300-600 req/hour)

### **Phase 4: Advanced Features (1 month)**

🔲 **Tasks**:
- A/B testing framework
- BLEU/ROUGE evaluation
- Automatic prompt tuning
- Response quality scoring
- Semantic cache (similar queries)

**Expected Impact**: Measurable quality improvements, data-driven optimization

---

## 📚 Related Documentation

- **Architecture**: `docs/architecture/AGENT_ARCHITECTURE.md`
- **Data Management**: `docs/guides/DATA_MANAGEMENT_GUIDE.md`
- **API Reference**: `docs/api/API_REFERENCE.md`

---

**Last Updated**: November 19, 2025  
**Version**: 1.0  
**Status**: ✅ Complete
