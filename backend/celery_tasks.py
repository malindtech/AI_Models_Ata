# backend/celery_tasks.py
"""
Celery tasks for background processing
Includes content generation with validation post-processing
"""
import time
import yaml
from pathlib import Path
from celery import Task
from loguru import logger

from backend.celery_app import celery_app
from backend.validators import validate_content, ValidationError
from scripts.llama_client import query_llama, OllamaError


PROMPTS_DIR = Path("prompts")


class CallbackTask(Task):
    """Base task with callbacks for tracking"""
    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"Task {task_id} succeeded")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {task_id} failed: {exc}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(f"Task {task_id} retrying: {exc}")


def classify_intent(message: str) -> dict:
    """
    Classify customer message intent using few-shot prompting
    Returns: {"intent": str, "latency_s": float}
    """
    template_path = PROMPTS_DIR / "intent_classifier.yaml"
    if not template_path.exists():
        raise FileNotFoundError("Intent classifier template not found")
    
    template = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    system = template.get("system_instructions", "")
    pattern = template.get("prompt_pattern", "")
    
    prompt = f"{system}\n\n{pattern}".replace("{message}", message).strip()
    
    try:
        r = query_llama(prompt, max_tokens=50, temperature=0.2)
    except OllamaError as e:
        raise Exception(f"Intent classification error: {e}")
    
    # Parse intent from response
    import json
    import re
    
    response_text = r["response"].strip()
    
    # Try to extract JSON
    try:
        if '{' in response_text and '}' in response_text:
            json_str = response_text[response_text.find('{'): response_text.rfind('}')+1]
            parsed = json.loads(json_str)
            intent = parsed.get("intent", "inquiry")
        else:
            intent = "inquiry"
    except:
        intent = "inquiry"
    
    # Validate intent
    valid_intents = ["complaint", "inquiry", "request"]
    if intent not in valid_intents:
        response_lower = response_text.lower()
        for valid_intent in valid_intents:
            if valid_intent in response_lower:
                intent = valid_intent
                break
        else:
            intent = "inquiry"
    
    logger.info(f"Intent classified: {intent}")
    return {"intent": intent, "latency_s": r["latency_s"]}


def generate_reply_from_intent(message: str, intent: str) -> dict:
    """
    Generate contextual reply based on message and detected intent
    
    Day 5: Enhanced with RAG context retrieval
    Returns: {"reply": str, "next_steps": str, "latency_s": float}
    """
    template_path = PROMPTS_DIR / "reply_generator.yaml"
    if not template_path.exists():
        raise FileNotFoundError("Reply generator template not found")
    
    template = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    system = template.get("system_instructions", "")
    pattern = template.get("prompt_pattern", "")
    
    prompt = f"{system}\n\n{pattern}".replace("{message}", message).replace("{intent}", intent).strip()
    
    # Day 5: Add RAG context retrieval
    try:
        from backend.vector_store import retrieve_similar, initialize_chroma_client
        from backend.rag_utils import prepare_rag_context, inject_rag_context
        
        # Initialize ChromaDB client (cached after first call)
        client = initialize_chroma_client()
        
        # Retrieve relevant support examples based on the message
        results = retrieve_similar("support", message, k=3, client=client)
        
        if results:
            # Prepare and inject RAG context
            context = prepare_rag_context(results, max_contexts=3)
            prompt = inject_rag_context(prompt, context)
            logger.info(f"✅ Injected {len(results)} RAG contexts for reply generation (intent: {intent})")
        else:
            logger.debug("No relevant RAG contexts found")
    
    except Exception as e:
        logger.warning(f"RAG retrieval failed, continuing without context: {e}")
        # Continue without RAG - graceful degradation
    
    try:
        r = query_llama(prompt, max_tokens=512, temperature=0.5)
    except OllamaError as e:
        raise Exception(f"Reply generation error: {e}")
    
    # Parse reply from response
    import json
    
    response_text = r["response"].strip()
    
    try:
        if '{' in response_text and '}' in response_text:
            json_str = response_text[response_text.find('{'): response_text.rfind('}')+1]
            parsed = json.loads(json_str)
            reply = parsed.get("reply", response_text)
            next_steps = parsed.get("next_steps", "")
        else:
            reply = response_text
            next_steps = ""
    except:
        reply = response_text
        next_steps = ""
    
    logger.info(f"Reply generated for intent {intent}")
    return {"reply": reply, "next_steps": next_steps, "latency_s": r["latency_s"]}


@celery_app.task(
    bind=True,
    base=CallbackTask,
    name="backend.celery_tasks.generate_reply_task",
    max_retries=3,
    default_retry_delay=10,  # 10 seconds between retries
    autoretry_for=(OllamaError, ConnectionError),
    retry_backoff=True,
    retry_backoff_max=60,  # Max 60 seconds backoff
    retry_jitter=True,
)
def generate_reply_task(self, message: str, max_validation_retries: int = 2) -> dict:
    """
    Background task: Generate reply with intent classification and validation
    
    Pipeline:
    1. Classify intent
    2. Generate reply based on intent
    3. Validate reply (length, forbidden phrases, toxicity)
    4. If validation fails → Retry generation (up to max_validation_retries times)
    5. Return result or rejection
    
    Args:
        message: Customer support message
        max_validation_retries: Max attempts to regenerate if validation fails (default: 2)
        
    Returns:
        Dict with reply data or validation error
    """
    logger.info(f"Starting reply generation task for message: {message[:50]}...")
    start_time = time.time()
    
    # Track all attempts for debugging
    generation_attempts = []
    
    try:
        # Step 1: Classify intent (only once)
        logger.info("Step 1: Classifying intent...")
        intent_result = classify_intent(message)
        detected_intent = intent_result["intent"]
        classification_latency = intent_result["latency_s"]
        
        # Step 2 & 3: Generate and validate (with retry loop)
        validation_attempt = 0
        max_attempts = max_validation_retries + 1  # Initial attempt + retries
        
        while validation_attempt < max_attempts:
            validation_attempt += 1
            
            logger.info(f"Step 2: Generating reply for intent '{detected_intent}' (attempt {validation_attempt}/{max_attempts})...")
            reply_result = generate_reply_from_intent(message, detected_intent)
            reply_text = reply_result["reply"]
            next_steps = reply_result["next_steps"]
            generation_latency = reply_result["latency_s"]
            
            # Store attempt for debugging
            attempt_info = {
                "attempt": validation_attempt,
                "reply": reply_text[:100] + "..." if len(reply_text) > 100 else reply_text,
                "generation_latency_s": generation_latency
            }
            
            # Step 3: Validate reply (POST-PROCESSING)
            logger.info(f"Step 3: Validating generated reply (attempt {validation_attempt})...")
            try:
                validation_result = validate_content(reply_text)
                logger.info(f"✅ Validation passed on attempt {validation_attempt} - content is safe")
                
                attempt_info["validation_result"] = "PASSED"
                generation_attempts.append(attempt_info)
                
                total_latency = time.time() - start_time
                
                # Return successful result
                return {
                    "status": "success",
                    "message": message,
                    "detected_intent": detected_intent,
                    "reply": reply_text,
                    "next_steps": next_steps,
                    "classification_latency_s": classification_latency,
                    "generation_latency_s": generation_latency,
                    "total_latency_s": total_latency,
                    "validation": validation_result,
                    "generation_attempts": validation_attempt,  # How many tries it took
                    "attempt_details": generation_attempts  # Full attempt history
                }
                
            except ValidationError as ve:
                # Validation failed
                logger.warning(f"❌ Validation failed on attempt {validation_attempt}: {ve.reason}")
                
                attempt_info["validation_result"] = "FAILED"
                attempt_info["failure_reason"] = ve.reason
                attempt_info["failure_details"] = ve.details
                generation_attempts.append(attempt_info)
                
                # Check if we should retry
                if validation_attempt < max_attempts:
                    logger.info(f"🔄 Retrying generation... ({max_attempts - validation_attempt} attempts remaining)")
                    # Loop continues to next attempt
                    continue
                else:
                    # All attempts exhausted - return failure
                    logger.error(f"❌ All {max_attempts} generation attempts failed validation")
                    
                    total_latency = time.time() - start_time
                    
                    # Return failure result with all attempt details
                    return {
                        "status": "validation_failed",
                        "message": message,
                        "detected_intent": detected_intent,
                        "generated_reply": reply_text,  # Last attempt
                        "validation_failure_reason": ve.reason,
                        "validation_details": ve.details,
                        "classification_latency_s": classification_latency,
                        "generation_latency_s": generation_latency,
                        "total_latency_s": total_latency,
                        "generation_attempts": validation_attempt,
                        "attempt_details": generation_attempts,  # All attempts with reasons
                        "error": f"Content validation failed after {validation_attempt} attempts: {ve.reason}"
                    }
    
    except Exception as e:
        logger.exception(f"Task execution error: {e}")
        
        # Check if we should retry
        if isinstance(e, (OllamaError, ConnectionError)):
            logger.warning(f"Retrying task due to: {e}")
            raise self.retry(exc=e)
        
        # Return error result
        total_latency = time.time() - start_time
        return {
            "status": "error",
            "message": message,
            "error": str(e),
            "total_latency_s": total_latency
        }


if __name__ == "__main__":
    # Local test (not as Celery task)
    print("Testing reply generation with validation...")
    
    # Test 1: Normal message
    result = generate_reply_task.apply(args=["My order hasn't arrived yet"]).get()
    print(f"\n✅ Test 1: {result['status']}")
    if result['status'] == 'success':
        print(f"Reply: {result['reply'][:100]}...")
    
    # Test 2: Message that might generate toxic content (edge case)
    # In practice, Llama should generate professional support replies
