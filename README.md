# AI Content Project - Customer Support Agent

## 📋 Project Overview

Production pipeline for a Customer Support Agent powered by **Llama 3** (8B model). This system generates intelligent, empathetic customer support responses using FastAPI and Ollama.

### Current Scope
- **Focus**: Customer Support Agent with synthetic data validation
- **Model**: Llama 3 (8B) via Ollama
- **Framework**: FastAPI for REST API endpoints
- **Future**: Content Generation Agent, RAG enhancement, real datasets

---

## 🏗️ Project Structure

```
ai-content-project/
├── backend/
│   ├── main.py                 # FastAPI application & endpoints
│   └── routes/                 # (Reserved for future route modules)
├── scripts/
│   ├── llama_client.py         # Ollama client with fallback logic
│   ├── support_smoketest.py    # Manual API testing script
│   └── ollama_smoketest.py     # Ollama connectivity test
├── prompts/
│   └── support_reply.yaml      # Customer support prompt template
├── tests/
│   └── test_support_agent.py   # Automated test suite
├── requirements.txt            # Python dependencies
├── .env                        # Environment configuration (create from .env.example)
└── README.md                   # This file
```

---

## 🚀 Quick Start

### 1. Prerequisites

- **Python 3.9+**
- **Ollama** installed and running
- **Llama 3 model** pulled (`ollama pull llama3:8b`)

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the project root:

```env
OLLAMA_URL=http://localhost:11434
MODEL_NAME=llama3:8b
FALLBACK_MODELS=llama3.2:3b,llama3:latest
```

### 4. Pull Llama 3 Model

```powershell
ollama pull llama3:8b
```

### 5. Start the API Server

```powershell
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: **http://localhost:8000**

---

## 📡 API Endpoints

### Health & Readiness

#### `GET /health`
Basic health check.

**Response:**
```json
{
  "status": "ok"
}
```

#### `GET /ready`
Verifies Ollama connectivity and model availability.

**Response:**
```json
{
  "model_ok": true,
  "latency_s": 0.234
}
```

#### `GET /test`
Quick test of Llama 3 generation.

**Response:**
```json
{
  "prompt": "Write a friendly one-line welcome message...",
  "reply": "Welcome! How can I assist you today?",
  "latency_s": 1.523
}
```

---

### Customer Support Generation

#### `POST /v1/generate/content`

Generates customer support replies using Llama 3.

**Request Body:**
```json
{
  "content_type": "support_reply",
  "topic": "unable to log into account",
  "tone": "empathetic"
}
```

**Parameters:**
- `content_type` (string): Always `"support_reply"` (fixed for customer support)
- `topic` (string, required): Customer issue or question
- `tone` (string, optional): Response tone - `"neutral"`, `"empathetic"`, `"formal"`, or `"friendly"` (default: `"neutral"`)

**Response:**
```json
{
  "content_type": "support_reply",
  "topic": "unable to log into account",
  "headline": "Account Login Assistance",
  "body": "I understand how frustrating it can be when you can't access your account. Let's get you back in right away. First, try resetting your password using the 'Forgot Password' link on the login page. If that doesn't work, please verify you're using the correct email address. If you're still having trouble, our support team is here to help 24/7.",
  "latency_s": 2.156
}
```

---

## 🧪 Testing & Validation

### Day 1 Acceptance Criteria

✅ **Llama 3 generates text successfully**
- Test with: `"Write one sentence about AI"`
- Validation: Run `python scripts/llama_client.py`

✅ **FastAPI runs on http://localhost:8000**
- Health check: `GET /health` returns `{"status": "ok"}`
- Readiness: `GET /ready` confirms model connectivity

✅ **`/v1/generate/content` returns structured JSON**
- Returns both `headline` and `body` fields
- Test payload: `{"content_type": "support_reply", "topic": "unable to log into account"}`

### Manual Testing

#### 1. Test Ollama Connection
```powershell
python scripts/ollama_smoketest.py
```

#### 2. Test Llama 3 Basic Generation
```powershell
python scripts/llama_client.py
```

#### 3. Test Customer Support Endpoint
```powershell
# Start the server first (in separate terminal)
cd backend
uvicorn main:app --reload --port 8000

# Run smoke test
python scripts/support_smoketest.py
```

**Environment Variables for Smoke Test:**
```powershell
$env:SUPPORT_TOPIC="password reset not working"
$env:SUPPORT_TONE="friendly"
python scripts/support_smoketest.py
```

### Automated Testing

Run the full test suite:
```powershell
pytest tests/test_support_agent.py -v
```

**Test Coverage:**
- ✅ Support reply contains both headline and body
- ✅ Response includes empathy markers and actionable steps
- ✅ API returns 200 status with valid structure

---

## 🎯 Test Scenarios

### Scenario 1: Login Issues
```json
{
  "topic": "unable to log into account",
  "tone": "empathetic"
}
```

### Scenario 2: Password Reset
```json
{
  "topic": "password reset not working",
  "tone": "empathetic"
}
```

### Scenario 3: Product Question
```json
{
  "topic": "how to track my order",
  "tone": "friendly"
}
```

### Scenario 4: Billing Inquiry
```json
{
  "topic": "unexpected charge on my account",
  "tone": "formal"
}
```

### Scenario 5: Technical Support
```json
{
  "topic": "app crashes when I try to upload photos",
  "tone": "neutral"
}
```

---

## 🛠️ Troubleshooting

### Issue: "Model not found"
**Solution:**
```powershell
ollama pull llama3:8b
```

### Issue: "Connection refused on port 11434"
**Solution:**
```powershell
ollama serve
```

### Issue: Slow responses
**Causes:**
- First request pulls model into memory (~4-5GB)
- Subsequent requests are much faster
- Adjust `max_tokens` and `temperature` in `llama_client.py`

### Issue: Import errors
**Solution:**
```powershell
# Ensure you're running from project root
$env:PYTHONPATH="d:\Malind Tech\AI System"
```

---

## 📊 Quality Assurance Checklist

- [ ] Ollama service is running (`ollama serve`)
- [ ] Llama 3:8b model is pulled
- [ ] Python dependencies installed
- [ ] FastAPI starts without errors
- [ ] `/health` endpoint returns 200
- [ ] `/ready` endpoint confirms model is loaded
- [ ] `/v1/generate/content` returns structured JSON
- [ ] Response includes `headline` and `body`
- [ ] Body contains empathy markers (when tone is empathetic)
- [ ] Body contains actionable steps
- [ ] All pytest tests pass

---

## 🔮 Future Enhancements

### Phase 2: Real Datasets
- Integrate real customer support ticket data
- Fine-tune prompts based on actual queries
- Add sentiment analysis

### Phase 3: RAG (Retrieval-Augmented Generation)
- Vector database integration (Pinecone/Chroma)
- Knowledge base for product documentation
- Context-aware responses

### Phase 4: Content Generation Agent
- Blog post generation
- Product description creation
- Multi-model pipeline

### Phase 5: Production Features
- Rate limiting
- Authentication
- Logging & monitoring
- Model performance metrics
- A/B testing framework

---

## 📝 API Documentation

Interactive API docs available when server is running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📄 License

MIT License - See LICENSE file for details

---

## 👥 Contributing

This is a learning project for building production AI pipelines. Contributions welcome!

---

## 🔗 Resources

- [Ollama Documentation](https://ollama.ai/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Llama 3 Model Card](https://ollama.ai/library/llama3)
- [Pydantic Documentation](https://docs.pydantic.dev/)

---

## 📅 Development Progress

### ✅ Day 1 - Basic Customer Support Agent (COMPLETE)
- ✅ Project setup & Ollama integration
- ✅ FastAPI endpoints (/health, /ready, /test)
- ✅ Content generation endpoint (/v1/generate/content)
- ✅ YAML prompt templates
- ✅ Synthetic data testing
- ✅ Automated test suite (pytest)

### ✅ Day 2 - Reply Agent & Intent Classifier (COMPLETE)
- ✅ Intent classification system (complaint/inquiry/request)
- ✅ Few-shot prompting implementation
- ✅ Reply generation with context awareness
- ✅ New endpoints: /v1/classify/intent, /v1/generate/reply
- ✅ Pipeline: classify → generate reply
- ✅ Comprehensive test suite

**New Endpoints (Day 2):**

#### `POST /v1/classify/intent`
Classify customer message intent.

**Request:**
```json
{
  "message": "My order hasn't arrived yet"
}
```

**Response:**
```json
{
  "intent": "complaint",
  "confidence": "high",
  "latency_s": 3.24
}
```

#### `POST /v1/generate/reply`
Full Reply Agent pipeline - classify intent and generate contextual response.

**Request:**
```json
{
  "message": "My order hasn't arrived yet"
}
```

**Response:**
```json
{
  "message": "My order hasn't arrived yet",
  "detected_intent": "complaint",
  "reply": "I sincerely apologize for the delay in your order...",
  "next_steps": "Please check your tracking number...",
  "classification_latency_s": 3.2,
  "generation_latency_s": 7.5,
  "total_latency_s": 10.7
}
```

**Day 2 Testing:**
```powershell
# Quick acceptance test
python scripts/day2_acceptance_test.py

# Comprehensive test suite
python scripts/test_day2_reply_agent.py

# Automated pytest
pytest tests/test_day2_reply_agent.py -v
```

See [DAY2_IMPLEMENTATION_GUIDE.md](DAY2_IMPLEMENTATION_GUIDE.md) for detailed documentation.

---

## 📄 License

MIT License - See LICENSE file for details

---

## 👥 Contributing

This is a learning project for building production AI pipelines. Contributions welcome!

---

**Status**: ✅ Day 1 & Day 2 Complete - Reply Agent with Intent Classification Operational
