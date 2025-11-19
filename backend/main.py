# backend/main.py
import os
import json
import re
from pathlib import Path
import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi import Body
from pydantic import BaseModel, Field
from typing import Literal, Optional, List
from dotenv import load_dotenv
from loguru import logger
from scripts.llama_client import query_llama, OllamaError
from collections import defaultdict
from datetime import datetime, timedelta
import time
import asyncio

# Day 3: Celery imports
try:
    from backend.celery_tasks import generate_reply_task
    from celery.result import AsyncResult
    from backend.celery_app import celery_app
    CELERY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Celery not available: {e}")
    CELERY_AVAILABLE = False

# Day 5: Vector DB imports
try:
    from backend.vector_store import (
        initialize_chroma_client,
        retrieve_similar,
        retrieve_cross_collection,
        create_or_get_collection
    )
    VECTOR_DB_AVAILABLE = True
    CHROMA_CLIENT = None  # Initialize on startup
except ImportError as e:
    logger.warning(f"Vector DB not available: {e}")
    VECTOR_DB_AVAILABLE = False
    CHROMA_CLIENT = None

# Production: Validator imports
from backend.validators import validate_support_reply

load_dotenv()

# ==== Rate Limiting Configuration ====
# In-memory rate limiting (use Redis for production multi-server deployments)
rate_limit_data = defaultdict(lambda: {"count": 0, "window_start": datetime.now(), "blocked_until": None})
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "100"))  # requests per window
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "3600"))  # 1 hour default
RATE_LIMIT_BLOCK_DURATION = int(os.getenv("RATE_LIMIT_BLOCK_DURATION", "300"))  # 5 min penalty

# ==== Conversation State Management ====
conversation_states = {}  # In-memory (use Redis/DB for production)
CONVERSATION_TIMEOUT_SECONDS = int(os.getenv("CONVERSATION_TIMEOUT_SECONDS", "1800"))  # 30 minutes

class ConversationState:
    """
    Track conversation state across multiple turns
    Stores extracted context, intent history, and turn management
    """
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.turns = []
        self.extracted_info = {}  # order_number, email, tracking, etc.
        self.last_intent = None
        self.intent_history = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.metadata = {}
    
    def add_turn(self, role: str, message: str, intent: str = None, reply_metadata: dict = None):
        """Add a conversation turn"""
        turn_data = {
            "role": role,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        if intent:
            turn_data["intent"] = intent
            self.last_intent = intent
            self.intent_history.append(intent)
        
        if reply_metadata:
            turn_data["metadata"] = reply_metadata
        
        self.turns.append(turn_data)
        self.updated_at = datetime.now()
        
        logger.debug(f"Added turn to conversation {self.conversation_id}: {role} - {message[:50]}...")
    
    def update_extracted_info(self, info: dict):
        """Update extracted information (order numbers, emails, etc.)"""
        self.extracted_info.update(info)
        self.updated_at = datetime.now()
        logger.debug(f"Updated conversation {self.conversation_id} info: {list(info.keys())}")
    
    def get_turn_history(self, max_turns: int = None) -> List[dict]:
        """Get conversation history, optionally limited"""
        if max_turns:
            return self.turns[-max_turns:]
        return self.turns
    
    def is_expired(self) -> bool:
        """Check if conversation has timed out"""
        elapsed = (datetime.now() - self.updated_at).total_seconds()
        return elapsed > CONVERSATION_TIMEOUT_SECONDS
    
    def to_dict(self) -> dict:
        """Serialize state to dict"""
        return {
            "conversation_id": self.conversation_id,
            "turns": self.turns,
            "extracted_info": self.extracted_info,
            "last_intent": self.last_intent,
            "intent_history": self.intent_history,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }

def get_or_create_conversation_state(conversation_id: str) -> ConversationState:
    """Get existing conversation state or create new one"""
    if conversation_id in conversation_states:
        state = conversation_states[conversation_id]
        if state.is_expired():
            logger.info(f"Conversation {conversation_id} expired, creating new state")
            del conversation_states[conversation_id]
            state = ConversationState(conversation_id)
            conversation_states[conversation_id] = state
        return state
    else:
        logger.info(f"Creating new conversation state: {conversation_id}")
        state = ConversationState(conversation_id)
        conversation_states[conversation_id] = state
        return state

def cleanup_expired_conversations():
    """Remove expired conversations from memory"""
    expired = [cid for cid, state in conversation_states.items() if state.is_expired()]
    for cid in expired:
        del conversation_states[cid]
        logger.info(f"Cleaned up expired conversation: {cid}")
    return len(expired)

# ==== Token Management ====
def calculate_token_budget(prompt_length: int, conversation_turns: int = 0, max_total: int = 4096) -> int:
    """
    Calculate appropriate max_tokens for LLM based on input size
    
    Args:
        prompt_length: Character length of prompt
        conversation_turns: Number of conversation turns
        max_total: Maximum total tokens (model context window)
    
    Returns:
        Recommended max_tokens for generation
    """
    # Rough estimation: 1 token ≈ 4 characters
    estimated_input_tokens = prompt_length // 4
    
    # Add overhead for conversation history
    conversation_overhead = conversation_turns * 50  # ~50 tokens per turn average
    
    total_input_estimate = estimated_input_tokens + conversation_overhead
    
    # Reserve tokens for output (at least 256, up to 1024)
    available_tokens = max_total - total_input_estimate
    
    # Clamp to reasonable ranges
    if available_tokens < 256:
        logger.warning(f"Very little token budget remaining ({available_tokens}), using minimum 256")
        return 256
    elif available_tokens > 1024:
        return 1024  # Cap at 1024 for response quality
    else:
        return available_tokens

def trim_messages_to_fit_token_limit(messages: List[dict], max_tokens: int = 3000) -> List[dict]:
    """
    Trim message history to fit within token budget
    Keeps most recent messages and ensures context fits
    
    Args:
        messages: List of message dicts
        max_tokens: Target token budget
    
    Returns:
        Trimmed message list
    """
    if not messages:
        return []
    
    # Estimate tokens (rough: 1 token ≈ 4 chars)
    def estimate_tokens(msg_list):
        total_chars = sum(len(m.get("message", "")) for m in msg_list)
        return total_chars // 4
    
    # If already within budget, return as-is
    current_tokens = estimate_tokens(messages)
    if current_tokens <= max_tokens:
        return messages
    
    # Trim from the beginning, keep most recent
    trimmed = messages.copy()
    while len(trimmed) > 1 and estimate_tokens(trimmed) > max_tokens:
        trimmed.pop(0)  # Remove oldest message
    
    logger.info(f"Trimmed conversation from {len(messages)} to {len(trimmed)} messages to fit token budget")
    return trimmed

def check_rate_limit(identifier: str) -> tuple[bool, dict]:
    """
    Check if request is within rate limit
    
    Args:
        identifier: Unique identifier (IP address, user ID, session ID, etc.)
    
    Returns:
        (allowed: bool, info: dict) where info contains:
            - remaining: requests remaining in window
            - retry_after: seconds until can retry (if blocked)
            - reset_at: timestamp when window resets
    """
    now = datetime.now()
    data = rate_limit_data[identifier]
    
    # Check if currently blocked
    if data["blocked_until"] and now < data["blocked_until"]:
        retry_after = int((data["blocked_until"] - now).total_seconds())
        logger.warning(f"Rate limit: {identifier} is blocked for {retry_after}s")
        return False, {
            "remaining": 0,
            "retry_after": retry_after,
            "reset_at": data["blocked_until"].isoformat()
        }
    
    # Reset window if expired
    window_elapsed = (now - data["window_start"]).total_seconds()
    if window_elapsed > RATE_LIMIT_WINDOW_SECONDS:
        data["count"] = 0
        data["window_start"] = now
        data["blocked_until"] = None
        logger.debug(f"Rate limit: Reset window for {identifier}")
    
    # Check if limit exceeded
    if data["count"] >= RATE_LIMIT_MAX_REQUESTS:
        # Block the identifier
        data["blocked_until"] = now + timedelta(seconds=RATE_LIMIT_BLOCK_DURATION)
        logger.warning(f"Rate limit: {identifier} exceeded limit ({data['count']}/{RATE_LIMIT_MAX_REQUESTS}), blocked until {data['blocked_until']}")
        return False, {
            "remaining": 0,
            "retry_after": RATE_LIMIT_BLOCK_DURATION,
            "reset_at": data["blocked_until"].isoformat()
        }
    
    # Increment counter
    data["count"] += 1
    remaining = RATE_LIMIT_MAX_REQUESTS - data["count"]
    reset_at = (data["window_start"] + timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)).isoformat()
    
    logger.debug(f"Rate limit: {identifier} request {data['count']}/{RATE_LIMIT_MAX_REQUESTS}, {remaining} remaining")
    
    return True, {
        "remaining": remaining,
        "retry_after": 0,
        "reset_at": reset_at
    }

def get_client_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting
    Priority: X-Forwarded-For header > X-Real-IP > direct client IP
    """
    # Check for forwarded IP (if behind proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For can contain multiple IPs, take the first
        return forwarded.split(",")[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct client
    return request.client.host if request.client else "unknown"

# ==== Production Utilities ====

def check_for_greeting(message: str) -> bool:
    """Detect if message contains a greeting"""
    greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 
                 'greetings', 'howdy', 'sup', "what's up", 'hiya', 'yo']
    message_lower = message.lower().strip()
    
    # Exact match
    if message_lower in greetings:
        return True
    
    # Starts with greeting
    for greeting in greetings:
        if message_lower.startswith(greeting):
            return True
    
    return False

def clean_conversation_messages(conversation_history: Optional[List[dict]], max_turns: int = 10) -> List[dict]:
    """
    Clean and limit conversation history for LLM consumption
    - Keep only role and message fields
    - Limit to last N turns to save tokens
    - Remove any metadata or timestamps
    """
    if not conversation_history:
        return []
    
    cleaned = []
    for turn in conversation_history[-max_turns:]:  # Last N turns only
        cleaned.append({
            "role": turn.get("role", "customer"),
            "message": turn.get("message", "")
        })
    
    return cleaned

def get_fallback_response(intent: str = "general", has_order_info: bool = False) -> dict:
    """
    Provide intelligent fallback responses when LLM fails
    Returns structured response matching normal reply format
    """
    fallbacks = {
        "complaint_with_order": "I apologize for the inconvenience. I'm having a momentary technical issue, but I've noted your order concern. Our team will review it and follow up with you within 2 hours via email.",
        "complaint_without_order": "I'm sorry you're experiencing this issue. I'm having a brief technical difficulty, but I can still help. Could you please provide your order number so I can escalate this to our team right away?",
        "inquiry": "I'm here to help! I'm experiencing a momentary connection issue. Could you please rephrase your question? I can assist with orders, shipping, returns, and product information.",
        "request_with_order": "I understand you need assistance. I'm having a brief technical issue, but I've received your request. Our team will process this and contact you within 4 hours.",
        "request_without_order": "I'd be happy to help with your request. I'm experiencing a brief technical issue, but to process this quickly, could you please provide your order number or account email?",
        "general": "I apologize, but I'm having a technical difficulty right now. Could you please try rephrasing your message? I'm here to help with any order or product questions."
    }
    
    # Select appropriate fallback
    if intent == "complaint":
        key = "complaint_with_order" if has_order_info else "complaint_without_order"
    elif intent == "request":
        key = "request_with_order" if has_order_info else "request_without_order"
    elif intent == "inquiry":
        key = "inquiry"
    else:
        key = "general"
    
    reply = fallbacks.get(key, fallbacks["general"])
    
    return {
        "reply": reply,
        "next_steps": "Please provide more details or try again",
        "latency_s": 0.0,
        "fallback_used": True
    }

def validate_llm_response(response_text: str) -> bool:
    """
    Validate LLM response meets minimum quality standards
    Returns True if response is acceptable, False if fallback needed
    """
    if not response_text or not isinstance(response_text, str):
        return False
    
    # Too short
    if len(response_text.strip()) < 10:
        return False
    
    # Response is JSON/error message
    if response_text.strip().startswith(("{", "[", "Error", "error", "ERROR", "Exception")):
        return False
    
    # Contains obvious error indicators
    error_indicators = ["traceback", "exception occurred", "failed to generate", "unable to generate", 
                       "connection error", "timeout error"]
    if any(indicator in response_text.lower() for indicator in error_indicators):
        return False
    
    return True

app = FastAPI(title="AI Content Project - Support Agent", version="0.1.0")

# Production: Statistics tracking
request_stats = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "rate_limited_requests": 0,
    "fallback_responses": 0,
    "average_latency_s": 0.0,
    "start_time": datetime.now()
}

# Check model configuration and warn if using small model
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2:1b")
if MODEL_NAME in ["llama3.2:1b", "llama2:1b"]:
    logger.warning("=" * 80)
    logger.warning("⚠️  WARNING: Using small model '{}'", MODEL_NAME)
    logger.warning("⚠️  For production use, switch to 'llama3:8b' for better quality")
    logger.warning("⚠️  Run: ollama pull llama3:8b")
    logger.warning("⚠️  Then set MODEL_NAME=llama3:8b in .env file")
    logger.warning("=" * 80)

# Day 5: Startup event to initialize vector database
@app.on_event("startup")
async def startup_event():
    """Initialize ChromaDB on startup with graceful degradation"""
    global CHROMA_CLIENT
    if VECTOR_DB_AVAILABLE:
        try:
            CHROMA_CLIENT = initialize_chroma_client()
            logger.info("✅ ChromaDB initialized successfully")
        except Exception as e:
            logger.error(f"⚠️ ChromaDB initialization failed: {e}")
            logger.warning("Vector search features will be unavailable")
            CHROMA_CLIENT = None
    else:
        logger.warning("Vector DB module not available - RAG features disabled")
    
    # Production: Start background cleanup task
    import asyncio
    asyncio.create_task(periodic_cleanup())
    logger.info("✅ Background cleanup task started")

async def periodic_cleanup():
    """Background task to periodically clean up expired conversations"""
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes
            cleaned = cleanup_expired_conversations()
            if cleaned > 0:
                logger.info(f"🧹 Cleaned up {cleaned} expired conversations")
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")

@app.get("/health")
def health():
    return {"status": "ok", "vector_db": CHROMA_CLIENT is not None}

@app.get("/ready")
def readiness():
    try:
        r = query_llama("Ping", max_tokens=8, temperature=0.0)
        return {"model_ok": bool(r["response"]), "latency_s": r["latency_s"]}
    except OllamaError as e:
        raise HTTPException(status_code=503, detail=f"Model unreachable: {e}")

@app.get("/v1/stats")
def get_statistics():
    """
    Production monitoring endpoint - returns system statistics
    """
    uptime = (datetime.now() - request_stats["start_time"]).total_seconds()
    
    # Calculate success rate
    total = request_stats["total_requests"]
    success_rate = (request_stats["successful_requests"] / total * 100) if total > 0 else 0.0
    
    # Active conversations
    active_conversations = len(conversation_states)
    expired_conversations = sum(1 for state in conversation_states.values() if state.is_expired())
    
    # Rate limiting stats
    active_rate_limits = sum(1 for data in rate_limit_data.values() 
                             if data["blocked_until"] and datetime.now() < data["blocked_until"])
    
    return {
        "uptime_seconds": round(uptime, 2),
        "requests": {
            "total": request_stats["total_requests"],
            "successful": request_stats["successful_requests"],
            "failed": request_stats["failed_requests"],
            "rate_limited": request_stats["rate_limited_requests"],
            "success_rate": round(success_rate, 2)
        },
        "responses": {
            "fallback_used": request_stats["fallback_responses"],
            "average_latency_s": round(request_stats["average_latency_s"], 3)
        },
        "conversations": {
            "active": active_conversations,
            "expired": expired_conversations,
            "timeout_seconds": CONVERSATION_TIMEOUT_SECONDS
        },
        "rate_limiting": {
            "active_blocks": active_rate_limits,
            "max_requests_per_window": RATE_LIMIT_MAX_REQUESTS,
            "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
            "block_duration_seconds": RATE_LIMIT_BLOCK_DURATION
        },
        "system": {
            "vector_db_available": CHROMA_CLIENT is not None,
            "celery_available": CELERY_AVAILABLE
        }
    }

@app.get("/test")
def test_llama():
    prompt = "Write a friendly one-line welcome message for a customer support chat."
    try:
        r = query_llama(prompt, max_tokens=60)
        return {"prompt": prompt, "reply": r["response"], "latency_s": r["latency_s"]}
    except OllamaError as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==== Content Generation Models & Endpoint ====

class GenerateContentRequest(BaseModel):
    content_type: Literal['blog', 'product_description', 'ad_copy', 'email_newsletter', 'social_media', 'support_reply'] = Field(..., description="Type of content to generate")
    topic: str = Field(..., description="Topic, product, or subject for content generation")
    tone: str = Field("neutral", description="Tone: neutral | empathetic | formal | friendly | professional | casual")

class GeneratedContent(BaseModel):
    headline: str
    body: str

class GenerateContentResponse(BaseModel):
    content_type: str
    topic: str
    headline: str
    body: str
    latency_s: float

PROMPTS_DIR = Path("prompts")

TEMPLATE_MAP = {
    "blog": PROMPTS_DIR / "blog_generator.yaml",
    "product_description": PROMPTS_DIR / "product_description.yaml",
    "ad_copy": PROMPTS_DIR / "ad_copy.yaml",
    "email_newsletter": PROMPTS_DIR / "email_newsletter.yaml",
    "social_media": PROMPTS_DIR / "social_media.yaml",
    "support_reply": PROMPTS_DIR / "support_reply.yaml",
}

def load_template(content_type: str):
    path = TEMPLATE_MAP.get(content_type)
    if not path or not path.exists():
        raise HTTPException(status_code=400, detail=f"Unknown content_type '{content_type}'")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data

def build_prompt(template: dict, content_type: str, topic: str, tone: str):
    system = template.get("system_instructions", "")
    pattern = template.get("prompt_pattern", "")
    
    # Map tone to style for templates that use {style}
    style_map = {
        "professional": "professional",
        "casual": "casual",
        "friendly": "casual",
        "formal": "professional",
        "neutral": "professional",
        "empathetic": "casual"
    }
    style = style_map.get(tone, "professional")
    
    # Provide default values for common template placeholders
    defaults = {
        "topic": topic,
        "tone": tone,
        "style": style,
        "length": "medium",
        "audience": "general readers"
    }
    
    # Replace placeholders using format with defaults
    try:
        prompt = pattern.format(**defaults)
    except KeyError as e:
        logger.warning(f"Missing placeholder in template: {e}")
        # Fallback to simple replace
        prompt = pattern.replace("{topic}", topic).replace("{tone}", tone)
    
    full = f"{system}\n\n{prompt}\n".strip()
    return full

def extract_json(raw: str) -> dict:
    # Attempt robust JSON parsing handling models that return JSON as a quoted string
    raw = raw.strip()
    
    # Remove markdown code blocks if present
    if raw.startswith('```'):
        # Remove opening ```json or ``` and closing ```
        lines = raw.split('\n')
        if lines[0].startswith('```'):
            lines = lines[1:]  # Remove first line
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]  # Remove last line
        raw = '\n'.join(lines).strip()
    
    # First pass: try to parse as-is
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            # Normalize field names: convert "title" to "headline" if present
            if "title" in data and "headline" not in data:
                data["headline"] = data["title"]
            return data
        if isinstance(data, str):
            # Second pass: the string itself may be JSON
            try:
                inner = json.loads(data)
                if isinstance(inner, dict):
                    # Normalize field names
                    if "title" in inner and "headline" not in inner:
                        inner["headline"] = inner["title"]
                    return inner
                else:
                    return {"headline": "(parse_error)", "body": data}
            except Exception:
                return {"headline": "(parse_error)", "body": data}
    except Exception:
        pass
    # Fallback: find JSON object braces within the text
    if '{' in raw and '}' in raw:
        candidate = raw[raw.find('{'): raw.rfind('}')+1]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                # Normalize field names
                if "title" in data and "headline" not in data:
                    data["headline"] = data["title"]
                return data
        except Exception:
            # If the candidate is an escaped JSON string, try unescape
            try:
                unescaped = bytes(candidate, 'utf-8').decode('unicode_escape')
                data = json.loads(unescaped)
                if isinstance(data, dict):
                    # Normalize field names
                    if "title" in data and "headline" not in data:
                        data["headline"] = data["title"]
                    return data
            except Exception:
                pass
    # If the entire payload is a quoted JSON string, try unquoting and unescaping
    if raw.startswith('"') and raw.endswith('"'):
        inner = raw[1:-1]
        try:
            unescaped = bytes(inner, 'utf-8').decode('unicode_escape')
            data = json.loads(unescaped)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    # Last resort: return whole text as body
    # Heuristic extraction: try to pull "headline"/"title" and "body" values from text
    try:
        # Try headline first, then title
        head_m = re.search(r'"(?:headline|title)"\s*:\s*"(.*?)"', raw, flags=re.DOTALL)
        body_m = re.search(r'"body"\s*:\s*"(.*?)"', raw, flags=re.DOTALL)
        headline = head_m.group(1) if head_m else "(parse_error)"
        body = body_m.group(1) if body_m else raw
        # Unescape common sequences
        headline = headline.replace('\\n', '\n').replace('\\"', '"')
        body = body.replace('\\n', '\n').replace('\\"', '"')
        return {"headline": headline, "body": body}
    except Exception:
        return {"headline": "(parse_error)", "body": raw}

@app.post("/v1/generate/content", response_model=GenerateContentResponse)
def generate_content(req: GenerateContentRequest = Body(...)):
    template = load_template(req.content_type)
    prompt = build_prompt(template, req.content_type, req.topic, req.tone)
    
    # Day 5: Add RAG context retrieval for enhanced generation
    if VECTOR_DB_AVAILABLE and CHROMA_CLIENT is not None:
        try:
            from backend.rag_utils import prepare_rag_context, inject_rag_context
            
            # Select appropriate collection based on content type
            collection_map = {
                "blog": "blogs",
                "product_description": "products",
                "ad_copy": "products",  # Use product examples for ad copy
                "email_newsletter": "blogs",  # Use blog content for newsletters
                "social_media": "social",
                "support_reply": "support"
            }
            
            collection = collection_map.get(req.content_type, "support")
            results = retrieve_similar(collection, req.topic, k=3, client=CHROMA_CLIENT)
            
            if results:
                # Prepare and inject RAG context
                context = prepare_rag_context(results, max_contexts=3)
                prompt = inject_rag_context(prompt, context)
                logger.info(f"✅ Injected {len(results)} RAG contexts from '{collection}' collection")
            else:
                logger.debug(f"No relevant contexts found in '{collection}' collection")
        
        except Exception as e:
            logger.warning(f"RAG retrieval failed, continuing without context: {e}")
            # Continue without RAG - graceful degradation
    
    # Debug: log full prompt being sent
    logger.debug(f"Sending prompt to Ollama (length: {len(prompt)} chars)")
    logger.debug(f"Full prompt:\n{'='*80}\n{prompt}\n{'='*80}")
    
    # Production: Dynamic token management based on content type and prompt length
    base_max_tokens = 1024 if req.content_type in ["blog", "email_newsletter"] else 512
    max_tokens = calculate_token_budget(len(prompt), max_total=4096)
    max_tokens = min(max_tokens, base_max_tokens)  # Don't exceed content type limits
    
    logger.debug(f"Using dynamic token budget: {max_tokens} tokens (prompt: {len(prompt)} chars)")
    
    try:
        r = query_llama(prompt, max_tokens=max_tokens, temperature=0.4)
    except OllamaError as e:
        raise HTTPException(status_code=502, detail=f"Model error: {e}")
    
    # Debug: log raw response
    logger.debug(f"Raw LLM response: {r['response'][:1000]}...")
    
    parsed = extract_json(r["response"]) or {}
    logger.debug(f"Parsed JSON keys: {list(parsed.keys())}")
    
    # Validate and extract content with production-grade fallbacks
    headline = parsed.get("headline") or parsed.get("title") or ""
    
    # Build body content - prioritize complete structured content
    body_parts = []
    
    # Extract introduction
    intro = parsed.get("introduction", "")
    if intro and isinstance(intro, str) and len(intro) > 20:
        body_parts.append(intro.strip())
    
    # Extract main body - this is the critical part
    body_raw = parsed.get("body") or parsed.get("content") or parsed.get("description") or ""
    
    if body_raw and isinstance(body_raw, str):
        # Clean up the body text
        body_text = body_raw.strip()
        
        # Remove JSON artifacts if present
        if body_text.startswith('{') or body_text.startswith('['):
            # Model returned metadata instead of content - this is a failure
            logger.warning("Model returned JSON/metadata instead of blog content")
            body_text = ""
        else:
            body_parts.append(body_text)
    
    # Extract conclusion
    conclusion = parsed.get("conclusion", "")
    if conclusion and isinstance(conclusion, str) and len(conclusion) > 20:
        body_parts.append(conclusion.strip())
    
    # Combine all parts
    body = "\n\n".join(body_parts) if body_parts else ""
    
    # PRODUCTION VALIDATION: Ensure minimum quality standards
    MIN_BODY_LENGTH = 200  # Minimum acceptable body length
    MIN_HEADLINE_LENGTH = 10
    
    if len(body) < MIN_BODY_LENGTH:
        logger.error(f"Generated content too short ({len(body)} chars). Model output was inadequate.")
        # Try to extract any meaningful text from raw response
        raw_text = r["response"].strip()
        
        # Remove JSON delimiters and markdown
        raw_text = re.sub(r'```[a-z]*\n?', '', raw_text)
        raw_text = re.sub(r'\{["\w:,\[\]\s]*\}', '', raw_text)
        
        if len(raw_text) > MIN_BODY_LENGTH:
            body = raw_text
            logger.info("Recovered content from raw response")
        else:
            # Last resort: generate meaningful error content
            raise HTTPException(
                status_code=422, 
                detail=f"Model generated insufficient content ({len(body)} chars). Consider using a larger model like llama3:8b for better results."
            )
    
    if not headline or len(headline) < MIN_HEADLINE_LENGTH:
        # Generate headline from topic as fallback
        headline = f"Complete Guide to {req.topic.title()}" if len(req.topic) < 50 else req.topic.title()
        logger.warning(f"Generated fallback headline: {headline}")
    
    # Clean up formatting
    body = re.sub(r'\n{3,}', '\n\n', body)
    body = body.strip()
    
    logger.debug(f"Final validated body length: {len(body)}")
    logger.info(f"Final output: headline='{headline[:50]}...', body_len={len(body)}")
    
    return GenerateContentResponse(
        content_type=req.content_type,
        topic=req.topic,
        headline=headline.strip(),
        body=body.strip(),
        latency_s=r["latency_s"],
    )

# ==== Day 5: RAG Retrieval Endpoint ====

class RetrieveRequest(BaseModel):
    query: str = Field(..., description="Search query for semantic retrieval")
    collection: Optional[str] = Field(None, description="Specific collection to search (blogs, products, support, social, reviews). If None, search all collections")
    top_k: int = Field(5, ge=1, le=20, description="Number of results to return (1-20)")

class RetrievedDocument(BaseModel):
    id: str = Field(..., description="Document ID")
    text: str = Field(..., description="Document text content")
    metadata: dict = Field(default_factory=dict, description="Document metadata")
    distance: float = Field(..., description="Cosine distance (lower is more similar)")
    collection: str = Field(..., description="Source collection name")

class RetrieveResponse(BaseModel):
    query: str
    collection: Optional[str]
    num_results: int
    results: List[RetrievedDocument]
    latency_ms: float

@app.post("/v1/retrieve", response_model=RetrieveResponse)
def retrieve_documents(req: RetrieveRequest = Body(...)):
    """
    Semantic search endpoint for RAG context retrieval
    
    Searches the vector database for documents similar to the query.
    Can search a specific collection or across all collections.
    """
    if not VECTOR_DB_AVAILABLE or CHROMA_CLIENT is None:
        raise HTTPException(
            status_code=503,
            detail="Vector database not available. Please check ChromaDB initialization."
        )
    
    import time
    start_time = time.time()
    
    try:
        if req.collection:
            # Search specific collection
            results = retrieve_similar(req.collection, req.query, k=req.top_k, client=CHROMA_CLIENT)
            
            # Format results
            documents = []
            for result in results:
                documents.append(RetrievedDocument(
                    id=result['id'],
                    text=result['text'],
                    metadata=result.get('metadata', {}),
                    distance=result['distance'],
                    collection=req.collection
                ))
        else:
            # Cross-collection search
            results = retrieve_cross_collection(
                req.query,
                k=req.top_k,
                client=CHROMA_CLIENT
            )
            
            # Format results
            documents = []
            for result in results:
                coll_name = result.get('metadata', {}).get('_collection', 'unknown')
                documents.append(RetrievedDocument(
                    id=result['id'],
                    text=result['text'],
                    metadata=result.get('metadata', {}),
                    distance=result['distance'],
                    collection=coll_name
                ))
        
        latency_ms = (time.time() - start_time) * 1000
        
        return RetrieveResponse(
            query=req.query,
            collection=req.collection,
            num_results=len(documents),
            results=documents,
            latency_ms=round(latency_ms, 2)
        )
        
    except Exception as e:
        logger.error(f"Retrieval error: {e}")
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")

# ==== Day 2: Reply Agent & Intent Classifier ====

class ConversationTurn(BaseModel):
    """Represents a single turn in a conversation"""
    role: Literal['customer', 'agent'] = Field(..., description="Role of the speaker")
    message: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="ISO 8601 timestamp of the message")

class GenerateReplyRequest(BaseModel):
    message: str = Field(..., description="Current customer support message/ticket to analyze and respond to")
    conversation_history: Optional[List[ConversationTurn]] = Field(
        None,
        description="Previous conversation turns for context (optional, enables multi-turn support)"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Unique conversation identifier for tracking multi-turn sessions (optional)"
    )

class IntentClassificationResponse(BaseModel):
    intent: Literal['complaint', 'inquiry', 'request'] = Field(..., description="Detected intent of the message")
    confidence: str = Field("high", description="Confidence level of classification")
    latency_s: float

class GenerateReplyResponse(BaseModel):
    message: str
    detected_intent: Literal['complaint', 'inquiry', 'request']
    reply: str
    next_steps: str
    classification_latency_s: float
    generation_latency_s: float
    total_latency_s: float
    conversation_id: Optional[str] = Field(None, description="Conversation ID if provided")
    turns_in_conversation: int = Field(1, description="Number of turns in this conversation")

# Day 3: Background task response models
class TaskSubmittedResponse(BaseModel):
    task_id: str = Field(..., description="Unique task ID for tracking")
    status: str = Field("pending", description="Initial status is always pending")
    message: str = Field(..., description="The original message submitted")

class TaskStatusResponse(BaseModel):
    task_id: str
    status: Literal['pending', 'processing', 'success', 'failed'] = Field(..., description="Current task status")
    result: Optional[dict] = Field(None, description="Task result if completed successfully")
    error: Optional[str] = Field(None, description="Error message if task failed")
    progress: Optional[dict] = Field(None, description="Progress information if available")

def classify_intent(message: str) -> dict:
    """
    Classify customer message intent using few-shot prompting
    Returns: {"intent": str, "latency_s": float}
    """
    # Load intent classifier template
    template_path = PROMPTS_DIR / "intent_classifier.yaml"
    if not template_path.exists():
        raise HTTPException(status_code=500, detail="Intent classifier template not found")
    
    template = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    system = template.get("system_instructions", "")
    pattern = template.get("prompt_pattern", "")
    
    # Build prompt with few-shot examples - use replace instead of format to avoid JSON brace issues
    prompt = f"{system}\n\n{pattern}".replace("{message}", message).strip()
    
    # Production: Try LLM classification with keyword-based fallback
    try:
        r = query_llama(prompt, max_tokens=50, temperature=0.2)  # Lower temp for classification
        
        # Parse intent from response
        parsed = extract_json(r["response"]) or {}
        intent = parsed.get("intent", "inquiry")  # Default to inquiry if parsing fails
        
        # Validate intent
        valid_intents = ["complaint", "inquiry", "request"]
        if intent not in valid_intents:
            # Try to find intent in raw response
            response_lower = r["response"].lower()
            for valid_intent in valid_intents:
                if valid_intent in response_lower:
                    intent = valid_intent
                    break
            else:
                intent = "inquiry"  # Fallback
        
        logger.info(f"Intent classified: {intent} for message: {message[:50]}...")
        return {"intent": intent, "latency_s": r["latency_s"]}
        
    except OllamaError as e:
        logger.error(f"LLM intent classification failed: {e}")
        # Fallback: Use keyword-based classification
        message_lower = message.lower()
        
        # Complaint indicators
        complaint_keywords = ['complaint', 'complain', 'unhappy', 'angry', 'disappointed', 'terrible', 
                             'awful', 'worst', 'horrible', 'unacceptable', 'frustrated', 'furious',
                             'disgusted', 'outraged', 'never again', 'poor service', 'bad experience']
        
        # Request indicators  
        request_keywords = ['return', 'refund', 'cancel', 'exchange', 'replace', 'want to', 'need to',
                           'can you', 'could you', 'please', 'help me', 'assist', 'change', 'update',
                           'modify', 'process', 'send me', 'give me']
        
        # Check complaint first (higher priority)
        if any(keyword in message_lower for keyword in complaint_keywords):
            intent = "complaint"
        # Then check request
        elif any(keyword in message_lower for keyword in request_keywords):
            intent = "request"
        # Default to inquiry
        else:
            intent = "inquiry"
        
        logger.warning(f"Using fallback keyword-based intent classification: {intent}")
        return {"intent": intent, "latency_s": 0.0}
    
    except Exception as e:
        logger.error(f"Unexpected error in intent classification: {e}")
        # Ultimate fallback - default to inquiry
        logger.warning("Using default intent: inquiry")
        return {"intent": "inquiry", "latency_s": 0.0}

def generate_reply_from_intent(message: str, intent: str, conversation_history: Optional[List[dict]] = None) -> dict:
    """
    Generate contextual reply based on message and detected intent
    
    Args:
        message: Current customer message
        intent: Detected intent (complaint/inquiry/request)
        conversation_history: Optional list of previous conversation turns
    
    Returns: {"reply": str, "next_steps": str, "latency_s": float}
    """
    # Step 1: Clean conversation history (limit to last 10 turns, remove metadata)
    cleaned_history = clean_conversation_messages(conversation_history, max_turns=10)
    
    # Step 2: Check for simple greetings/small talk first (only if no conversation history)
    message_lower = message.lower().strip()
    simple_greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening']
    
    # Only use canned greeting if it's truly just a greeting with no context
    if not cleaned_history and (message_lower in simple_greetings or 
       (len(message_lower) < 20 and any(g in message_lower for g in ['hi', 'hello', 'hey']) and 
        not any(word in message_lower for word in ['order', 'package', 'delivery', 'return', 'refund', 'help', 'issue', 'problem']))):
        return {
            "reply": "Hello! I'm here to help you with any questions or concerns about your order. How can I assist you today?",
            "next_steps": "Please let me know what you need help with",
            "latency_s": 0.0
        }
    
    # Load reply generator template
    template_path = PROMPTS_DIR / "reply_generator.yaml"
    if not template_path.exists():
        raise HTTPException(status_code=500, detail="Reply generator template not found")
    
    template = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    system = template.get("system_instructions", "")
    pattern = template.get("prompt_pattern", "")
    intent_guidelines = template.get("intent_guidelines", {})
    
    # Get intent-specific guidance
    intent_guide = intent_guidelines.get(intent, {})
    required_info = intent_guide.get("required_info", "")
    example = intent_guide.get("example", "")
    
    # Extract key information from message and history
    def extract_context_info(text: str) -> dict:
        """Extract order numbers, emails, tracking numbers from text"""
        info = {}
        # Order number patterns: ABC-1234, #12345, order 12345
        order_match = re.search(r'(?:order\s*#?\s*)?([A-Z]{2,4}-\d{4,6}|\#\d{4,8}|\b\d{6,10}\b)', text, re.IGNORECASE)
        if order_match:
            info['order_number'] = order_match.group(1).strip('#')
        
        # Email pattern
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            info['email'] = email_match.group(0)
        
        # Tracking number pattern
        tracking_match = re.search(r'(?:tracking|track)[\s#:]*([A-Z0-9]{10,})', text, re.IGNORECASE)
        if tracking_match:
            info['tracking'] = tracking_match.group(1)
        
        return info
    
    # Extract from current message
    current_info = extract_context_info(message)
    
    # Extract from cleaned conversation history
    history_info = {}
    if cleaned_history:
        for turn in cleaned_history:
            turn_info = extract_context_info(turn.get('message', ''))
            history_info.update(turn_info)  # Merge all extracted info
    
    # Combined context
    all_info = {**history_info, **current_info}  # Current message overrides history
    has_order_number = 'order_number' in all_info
    has_email = 'email' in all_info
    
    # Build enhanced prompt
    if cleaned_history and len(cleaned_history) > 0:
        # Format conversation history (use cleaned history)
        history_text = "\n".join([
            f"{turn['role'].title()}: {turn['message']}"
            for turn in cleaned_history  # Already limited to 10 turns
        ])
        
        # Build context summary
        context_summary = []
        if has_order_number:
            context_summary.append(f"Order Number: {all_info['order_number']}")
        if has_email:
            context_summary.append(f"Email: {all_info['email']}")
        if 'tracking' in all_info:
            context_summary.append(f"Tracking: {all_info['tracking']}")
        
        context_text = "\n".join(context_summary) if context_summary else "No key information extracted yet"
        
        # Multi-turn context-aware prompt with explicit conversation context
        prompt = f"""{system}

CONVERSATION CONTEXT:
You are continuing an ongoing conversation. The customer has already interacted with you before.
- Review the full conversation history below to understand what has been discussed
- Maintain consistency with previous responses
- DO NOT repeat information or questions already covered
- Reference specific prior exchanges when relevant (e.g., "As you mentioned earlier...")

CONVERSATION HISTORY (last {len(cleaned_history)} turns):
{history_text}

CURRENT MESSAGE:
Customer: {message}

DETECTED INTENT: {intent}

EXTRACTED INFORMATION:
{context_text}

INTENT GUIDELINES FOR {intent.upper()}:
{example}

CRITICAL INSTRUCTIONS:
1. ANALYZE what information you have:
   - If you have order number: Use it! Say "I've located order [NUMBER]" then take action
   - If missing and needed: Ask for it clearly
   
2. RESPOND appropriately to the customer's actual message:
   - If they provided info: Acknowledge it and take next step
   - If they asked a question: Answer it directly
   - If they have a problem: Show empathy and solve it
   
3. BE NATURAL - Don't sound robotic:
   - ✓ "Thanks for providing your order number. Let me check that for you now..."
   - ✓ "I see you're asking about [topic]. Here's what I can help with..."
   - ✗ "As per the protocol, I will now proceed to..."
   
4. NEVER:
   - Repeat information customer already provided
   - Ask questions already answered
   - Make up details not mentioned (timeframes, reasons, etc.)
   - Say "as discussed" without referencing specific info
   
5. ALWAYS:
   - Address what customer actually said
   - Provide specific, actionable next steps
   - Give realistic timeframes when promising action

Return ONLY valid JSON: {{"reply": "your natural, helpful response", "next_steps": "what happens next"}}
""".strip()
        
        logger.info(f"Multi-turn mode: {len(cleaned_history)} turns, extracted_info={list(all_info.keys())}")
    else:
        # Single-turn prompt - first interaction
        context_text = []
        if has_order_number:
            context_text.append(f"Order Number: {all_info['order_number']}")
        if has_email:
            context_text.append(f"Email: {all_info['email']}")
        
        info_status = "\n".join(context_text) if context_text else "No order/account info provided yet"
        
        prompt = f"""{system}

CUSTOMER MESSAGE:
{message}

DETECTED INTENT: {intent}

EXTRACTED INFORMATION:
{info_status}

INTENT GUIDELINES:
{example}

INSTRUCTIONS:
1. READ the customer's message carefully and respond to what they actually said
2. If they provided order number/email: Acknowledge it and take action
3. If missing and you need it: Ask for it politely and explain why
4. Be conversational and natural - you're a human support agent, not a robot
5. Provide specific next steps with realistic timeframes

Examples of GOOD responses:
- Customer: "Package hasn't arrived" → You: "I'm sorry to hear that! To track it down, could you provide your order number?"
- Customer: "My order ABC-123 is late" → You: "Thanks for providing order ABC-123. Let me check the shipping status right now and I'll have an update for you within 30 minutes."
- Customer: "Can I return this?" → You: "Absolutely! I can help with that. To process your return, I'll need your order number. Once I have that, I'll email you a prepaid return label within 15 minutes."

Return ONLY valid JSON: {{"reply": "your natural response", "next_steps": "what to do next"}}
""".strip()
        
        logger.debug(f"Single-turn mode, extracted_info={list(all_info.keys())}")
    
    # Production: Dynamic token management
    num_turns = len(cleaned_history) if cleaned_history else 0
    max_tokens = calculate_token_budget(len(prompt), conversation_turns=num_turns, max_total=4096)
    max_tokens = min(max_tokens, 768)  # Cap reply generation at 768 tokens
    
    logger.debug(f"Reply generation using {max_tokens} tokens (prompt: {len(prompt)} chars, turns: {num_turns})")
    
    # Try to generate response with LLM, fall back if it fails
    llm_latency = 0.0  # Track LLM latency
    try:
        r = query_llama(prompt, max_tokens=max_tokens, temperature=0.5)
        llm_latency = r.get("latency_s", 0.0)
        
        # Log raw response for debugging
        logger.debug(f"Raw LLM response: {r['response'][:200]}...")
        
        # Parse reply from response
        parsed = extract_json(r["response"]) or {}
        logger.debug(f"Parsed JSON: {parsed}")
        
        # Extract reply - handle if reply itself is JSON string
        reply = parsed.get("reply", r["response"])
        
        # If reply is still JSON string, try to parse it again
        if isinstance(reply, str) and reply.startswith("{"):
            try:
                reply_parsed = json.loads(reply)
                if isinstance(reply_parsed, dict) and "reply" in reply_parsed:
                    reply = reply_parsed["reply"]
                    logger.warning("Reply was double-encoded JSON, extracted inner reply")
            except:
                pass  # Not JSON, use as-is
        
        # Validate the generated response
        if not validate_llm_response(reply):
            logger.warning(f"LLM response failed validation: {reply[:100]}")
            # Use fallback response
            reply = get_fallback_response(intent, has_order_number)
            logger.info(f"Using fallback response for intent={intent}")
            
    except OllamaError as e:
        logger.error(f"LLM generation failed: {e}")
        # Use fallback response on error
        reply = get_fallback_response(intent, has_order_number)
        parsed = {}  # Reset parsed to empty since LLM failed
        logger.info(f"Using fallback response after LLM error for intent={intent}")
    except Exception as e:
        logger.error(f"Unexpected error during reply generation: {e}")
        # Generic fallback for any other error
        reply = get_fallback_response(intent, has_order_number)
        parsed = {}
        logger.info(f"Using fallback response after unexpected error for intent={intent}")
    
    next_steps = parsed.get("next_steps", "")
    
    # Production validation: Only add fallback if truly needed
    # Don't add if we already have order info from message or history
    needs_order = intent in ["complaint", "request"]
    
    if needs_order and not has_order_number:
        # Check if reply already asks for order number
        asks_for_order = any(phrase in reply.lower() for phrase in [
            'order number', 'order #', 'provide your order', 'provide the order',
            'could you provide', 'can you share', 'please provide', 'what is your order',
            'which order', 'share your order'
        ])
        
        if not asks_for_order:
            # Model forgot to ask - add fallback
            reply += " To help you with this, could you please provide your order number?"
            logger.warning(f"Added fallback request for order number (intent={intent})")
        else:
            logger.debug("Reply already asks for order info")
    elif has_order_number:
        logger.debug(f"Order number already provided: {all_info.get('order_number')} - no fallback needed")
    
    logger.info(f"Reply generated for intent={intent}, has_order={has_order_number}: {reply[:80]}...")
    return {"reply": reply, "next_steps": next_steps, "latency_s": llm_latency}

@app.post("/v1/classify/intent", response_model=IntentClassificationResponse)
def classify_intent_endpoint(req: GenerateReplyRequest = Body(...), request: Request = None):
    """
    Classify the intent of a customer support message
    """
    # Rate limiting check
    if request:
        client_id = get_client_identifier(request)
        allowed, rate_info = check_rate_limit(client_id)
        
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Retry after {rate_info['retry_after']} seconds.",
                headers={
                    "X-RateLimit-Limit": str(RATE_LIMIT_MAX_REQUESTS),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": rate_info["reset_at"],
                    "Retry-After": str(rate_info["retry_after"])
                }
            )
    
    result = classify_intent(req.message)
    return IntentClassificationResponse(
        intent=result["intent"],
        confidence="high",
        latency_s=result["latency_s"]
    )

@app.post("/v1/generate/reply")
def generate_reply(req: GenerateReplyRequest = Body(...), async_mode: bool = True, request: Request = None):
    """
    Reply Agent Pipeline:
    1. Classify intent of the message
    2. Generate contextually appropriate reply based on intent
    
    Day 3 Update:
    - Default: Submit as background Celery task (async_mode=True)
    - Returns task_id for polling via /v1/tasks/{task_id}
    - Fallback: Synchronous processing if Celery unavailable (async_mode=False)
    
    Production: Rate limiting applied
    """
    # Rate limiting check
    if request:
        client_id = get_client_identifier(request)
        allowed, rate_info = check_rate_limit(client_id)
        
        if not allowed:
            request_stats["rate_limited_requests"] += 1
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Retry after {rate_info['retry_after']} seconds.",
                headers={
                    "X-RateLimit-Limit": str(RATE_LIMIT_MAX_REQUESTS),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": rate_info["reset_at"],
                    "Retry-After": str(rate_info["retry_after"])
                }
            )
    
    # Track request
    request_stats["total_requests"] += 1
    
    # Day 3: Background task mode (default)
    if async_mode and CELERY_AVAILABLE:
        logger.info(f"Submitting reply generation as background task for: {req.message[:50]}...")
        
        # Convert conversation history to dict format for Celery serialization
        conversation_history = None
        if req.conversation_history:
            conversation_history = [turn.dict() for turn in req.conversation_history]
            logger.info(f"Including {len(conversation_history)} previous turns in task")
        
        # Submit task to Celery with conversation history
        task = generate_reply_task.delay(req.message, conversation_history=conversation_history)
        
        logger.info(f"Task submitted with ID: {task.id}")
        
        return TaskSubmittedResponse(
            task_id=task.id,
            status="pending",
            message=req.message
        )
    
    # Fallback: Synchronous mode (Day 2 behavior)
    logger.warning("Running in synchronous mode (Celery unavailable or async_mode=False)")
    
    start_time = time.time()
    
    # Production: Manage conversation state if conversation_id provided
    conversation_state = None
    if req.conversation_id:
        conversation_state = get_or_create_conversation_state(req.conversation_id)
        logger.info(f"Using conversation state {req.conversation_id} with {len(conversation_state.turns)} existing turns")
    
    # Step 1: Classify intent
    intent_result = classify_intent(req.message)
    detected_intent = intent_result["intent"]
    classification_latency = intent_result["latency_s"]
    
    # Step 2: Generate reply based on intent (with conversation history if provided)
    conversation_history = None
    if req.conversation_history:
        conversation_history = [turn.dict() for turn in req.conversation_history]
    elif conversation_state:
        # Use conversation state history if no explicit history provided
        conversation_history = conversation_state.get_turn_history(max_turns=10)
    
    reply_result = generate_reply_from_intent(req.message, detected_intent, conversation_history)
    generation_latency = reply_result["latency_s"]
    
    # Production: Update conversation state with this exchange
    if conversation_state:
        # Add customer message
        conversation_state.add_turn("customer", req.message, intent=detected_intent)
        
        # Add agent reply
        conversation_state.add_turn(
            "agent",
            reply_result["reply"],
            reply_metadata={
                "latency_s": generation_latency,
                "fallback_used": reply_result.get("fallback_used", False)
            }
        )
        
        # Extract and store any info from message
        def extract_context_info(text: str) -> dict:
            """Extract order numbers, emails, tracking numbers from text"""
            info = {}
            order_match = re.search(r'(?:order\s*#?\s*)?([A-Z]{2,4}-\d{4,6}|\#\d{4,8}|\b\d{6,10}\b)', text, re.IGNORECASE)
            if order_match:
                info['order_number'] = order_match.group(1).strip('#')
            email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
            if email_match:
                info['email'] = email_match.group(0)
            return info
        
        extracted = extract_context_info(req.message)
        if extracted:
            conversation_state.update_extracted_info(extracted)
    
    # Production validation: Check reply quality
    validation = validate_support_reply(
        reply=reply_result["reply"],
        intent=detected_intent,
        message=req.message,
        conversation_history=conversation_history or []
    )
    
    # Log quality issues
    if not validation["is_valid"]:
        logger.warning(f"Reply quality issues (score={validation['quality_score']:.2f}): {validation['issues']}")
        request_stats["failed_requests"] += 1
        # Note: We still return the reply but log the quality concerns
    else:
        logger.info(f"Reply passed quality validation (score={validation['quality_score']:.2f})")
        request_stats["successful_requests"] += 1
    
    # Track fallback usage
    if reply_result.get("fallback_used"):
        request_stats["fallback_responses"] += 1
    
    # Update average latency
    total_latency = time.time() - start_time
    if request_stats["total_requests"] > 0:
        current_avg = request_stats["average_latency_s"]
        count = request_stats["total_requests"]
        request_stats["average_latency_s"] = (current_avg * (count - 1) + total_latency) / count
    
    # Calculate total turns including current message
    turns_count = 1
    if req.conversation_history:
        turns_count = len(req.conversation_history) + 1
    
    return GenerateReplyResponse(
        message=req.message,
        detected_intent=detected_intent,
        reply=reply_result["reply"],
        next_steps=reply_result["next_steps"],
        classification_latency_s=classification_latency,
        generation_latency_s=generation_latency,
        total_latency_s=total_latency,
        conversation_id=req.conversation_id,
        turns_in_conversation=turns_count
    )


@app.get("/v1/tasks/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str):
    """
    Get status and result of a background task
    
    Day 3: Task Status Endpoint
    - Returns: pending, processing, success, or failed
    - If success: includes full result with reply
    - If failed: includes error message
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Background task system unavailable (Celery not configured)"
        )
    
    # Get task result from Celery
    task_result = AsyncResult(task_id, app=celery_app)
    
    # Check task state
    if task_result.state == "PENDING":
        # Task not started or doesn't exist
        return TaskStatusResponse(
            task_id=task_id,
            status="pending",
            progress={"message": "Task is queued and waiting to be processed"}
        )
    
    elif task_result.state == "STARTED":
        # Task is currently being processed
        return TaskStatusResponse(
            task_id=task_id,
            status="processing",
            progress={"message": "Task is currently being processed"}
        )
    
    elif task_result.state == "SUCCESS":
        # Task completed successfully
        result_data = task_result.result
        
        # Check if validation failed
        if result_data.get("status") == "validation_failed":
            return TaskStatusResponse(
                task_id=task_id,
                status="failed",
                error=result_data.get("error", "Content validation failed"),
                result=result_data  # Include details of what failed
            )
        
        # Successful with valid content
        return TaskStatusResponse(
            task_id=task_id,
            status="success",
            result=result_data
        )
    
    elif task_result.state == "FAILURE":
        # Task failed with exception
        error_msg = str(task_result.info) if task_result.info else "Unknown error"
        return TaskStatusResponse(
            task_id=task_id,
            status="failed",
            error=error_msg
        )
    
    elif task_result.state == "RETRY":
        # Task is being retried
        return TaskStatusResponse(
            task_id=task_id,
            status="processing",
            progress={"message": "Task is being retried after an error"}
        )
    
    else:
        # Unknown state
        return TaskStatusResponse(
            task_id=task_id,
            status="pending",
            progress={"message": f"Task state: {task_result.state}"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
