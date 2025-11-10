# backend/main.py
import os
import json
import re
from pathlib import Path
import yaml
from fastapi import FastAPI, HTTPException
from fastapi import Body
from pydantic import BaseModel, Field
from typing import Literal
from dotenv import load_dotenv
from loguru import logger
from scripts.llama_client import query_llama, OllamaError

load_dotenv()

app = FastAPI(title="AI Content Project - Support Agent", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok"}

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
    content_type: Literal['support_reply'] = Field('support_reply', description="Fixed: only 'support_reply' supported for customer support agent focus")
    topic: str = Field(..., description="Customer issue or question to address")
    tone: str = Field("neutral", description="Tone: neutral | empathetic | formal | friendly")

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
    # Only support replies currently in scope; others retained for future extension
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
    # Allow {tone} placeholder for support_reply
    prompt = pattern.format(topic=topic, tone=tone)
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

@app.post("/v1/generate/reply", response_model=GenerateReplyResponse)
def generate_reply(req: GenerateReplyRequest = Body(...)):
    """
    Reply Agent Pipeline:
    1. Classify intent of the message
    2. Generate contextually appropriate reply based on intent
    """
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
