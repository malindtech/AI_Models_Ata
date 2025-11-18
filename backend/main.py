# backend/main.py
import os
import json
import re
from pathlib import Path
import yaml
from fastapi import FastAPI, HTTPException
from fastapi import Body
from pydantic import BaseModel, Field
from typing import Literal, Optional, List
from dotenv import load_dotenv
from loguru import logger
from scripts.llama_client import query_llama, OllamaError

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

load_dotenv()

app = FastAPI(title="AI Content Project - Support Agent", version="0.1.0")

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
    
    # Replace placeholders in prompt pattern
    prompt = pattern.replace("{topic}", topic).replace("{tone}", tone)
    
    # For backward compatibility with format-style placeholders
    try:
        prompt = pattern.format(topic=topic, tone=tone)
    except KeyError:
        # If format fails, use replace (already done above)
        pass
    
    full = f"{system}\n\n{prompt}\n".strip()
    return full

def extract_json(raw: str) -> dict:
    # Attempt robust JSON parsing handling models that return JSON as a quoted string
    raw = raw.strip()
    # First pass: try to parse as-is
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            # Second pass: the string itself may be JSON
            try:
                inner = json.loads(data)
                if isinstance(inner, dict):
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
                return data
        except Exception:
            # If the candidate is an escaped JSON string, try unescape
            try:
                unescaped = bytes(candidate, 'utf-8').decode('unicode_escape')
                data = json.loads(unescaped)
                if isinstance(data, dict):
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
    # Heuristic extraction: try to pull "headline" and "body" values from text
    try:
        head_m = re.search(r'"headline"\s*:\s*"(.*?)"', raw, flags=re.DOTALL)
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
    
    try:
        r = query_llama(prompt, max_tokens=512, temperature=0.4)
    except OllamaError as e:
        raise HTTPException(status_code=502, detail=f"Model error: {e}")
    
    parsed = extract_json(r["response"]) or {}
    headline = parsed.get("headline") or "Untitled"
    body = parsed.get("body") or parsed.get("content") or r["response"]
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

class GenerateReplyRequest(BaseModel):
    message: str = Field(..., description="Customer support message/ticket to analyze and respond to")

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
    
    try:
        r = query_llama(prompt, max_tokens=50, temperature=0.2)  # Lower temp for classification
    except OllamaError as e:
        raise HTTPException(status_code=502, detail=f"Intent classification error: {e}")
    
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

def generate_reply_from_intent(message: str, intent: str) -> dict:
    """
    Generate contextual reply based on message and detected intent
    Returns: {"reply": str, "next_steps": str, "latency_s": float}
    """
    # Load reply generator template
    template_path = PROMPTS_DIR / "reply_generator.yaml"
    if not template_path.exists():
        raise HTTPException(status_code=500, detail="Reply generator template not found")
    
    template = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    system = template.get("system_instructions", "")
    pattern = template.get("prompt_pattern", "")
    
    # Build prompt with message and intent - use replace to avoid JSON brace issues
    prompt = f"{system}\n\n{pattern}".replace("{message}", message).replace("{intent}", intent).strip()
    
    try:
        r = query_llama(prompt, max_tokens=512, temperature=0.5)
    except OllamaError as e:
        raise HTTPException(status_code=502, detail=f"Reply generation error: {e}")
    
    # Parse reply from response
    parsed = extract_json(r["response"]) or {}
    reply = parsed.get("reply", r["response"])
    next_steps = parsed.get("next_steps", "")
    
    logger.info(f"Reply generated for intent {intent}: {reply[:50]}...")
    return {"reply": reply, "next_steps": next_steps, "latency_s": r["latency_s"]}

@app.post("/v1/classify/intent", response_model=IntentClassificationResponse)
def classify_intent_endpoint(req: GenerateReplyRequest = Body(...)):
    """
    Classify the intent of a customer support message
    """
    result = classify_intent(req.message)
    return IntentClassificationResponse(
        intent=result["intent"],
        confidence="high",
        latency_s=result["latency_s"]
    )

@app.post("/v1/generate/reply")
def generate_reply(req: GenerateReplyRequest = Body(...), async_mode: bool = True):
    """
    Reply Agent Pipeline:
    1. Classify intent of the message
    2. Generate contextually appropriate reply based on intent
    
    Day 3 Update:
    - Default: Submit as background Celery task (async_mode=True)
    - Returns task_id for polling via /v1/tasks/{task_id}
    - Fallback: Synchronous processing if Celery unavailable (async_mode=False)
    """
    # Day 3: Background task mode (default)
    if async_mode and CELERY_AVAILABLE:
        logger.info(f"Submitting reply generation as background task for: {req.message[:50]}...")
        
        # Submit task to Celery
        task = generate_reply_task.delay(req.message)
        
        logger.info(f"Task submitted with ID: {task.id}")
        
        return TaskSubmittedResponse(
            task_id=task.id,
            status="pending",
            message=req.message
        )
    
    # Fallback: Synchronous mode (Day 2 behavior)
    logger.warning("Running in synchronous mode (Celery unavailable or async_mode=False)")
    
    import time
    start_time = time.time()
    
    # Step 1: Classify intent
    intent_result = classify_intent(req.message)
    detected_intent = intent_result["intent"]
    classification_latency = intent_result["latency_s"]
    
    # Step 2: Generate reply based on intent
    reply_result = generate_reply_from_intent(req.message, detected_intent)
    generation_latency = reply_result["latency_s"]
    
    total_latency = time.time() - start_time
    
    return GenerateReplyResponse(
        message=req.message,
        detected_intent=detected_intent,
        reply=reply_result["reply"],
        next_steps=reply_result["next_steps"],
        classification_latency_s=classification_latency,
        generation_latency_s=generation_latency,
        total_latency_s=total_latency
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
