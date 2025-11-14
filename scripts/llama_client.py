# scripts/llama_client.py
import os
import time
import httpx
from typing import Dict, Any
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# Support both OLLAMA_BASE_URL (Docker) and OLLAMA_URL (local)
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_URL", "http://localhost:11434")
# Default to a commonly available model; can be overridden via .env
# Note: Llama 3 3B is published under the tag "llama3.2:3b" (not "llama3:3b").
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2:1b")
# Optional comma-separated fallback list, tried when the primary model isn't found
FALLBACK_MODELS = [m.strip() for m in os.getenv("FALLBACK_MODELS", "llama3.2:3b,llama3:latest").split(",") if m.strip()]
# Bump timeout for slower machines/network
TIMEOUT = 60

class OllamaError(Exception):
    pass

def query_llama(prompt: str, max_tokens: int = 128, temperature: float = 0.3, model: str | None = None) -> Dict[str, Any]:
    """
    Query Ollama generate endpoint. Returns dict: {response, latency_s, raw}
    """
    url = f"{OLLAMA_URL}/api/generate"

    # Build candidate model list: explicit param -> env/default -> fallbacks
    models_to_try = []
    if model:
        models_to_try.append(model)
    else:
        models_to_try.append(MODEL_NAME)
    for m in FALLBACK_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    start = time.time()
    with httpx.Client(timeout=TIMEOUT) as client:
        for idx, model_name in enumerate(models_to_try):
            payload = {
                "model": model_name,
                "prompt": prompt,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                },
                # Request a single non-streaming JSON response to simplify parsing
                "stream": False,
            }
            try:
                r = client.post(url, json=payload)
                # If model not found, Ollama often returns 404 or 400 with a message
                if r.status_code == 404 or (r.status_code == 400 and "not found" in r.text.lower()):
                    logger.warning("Model '%s' not found, trying next fallback...", model_name)
                    last_error = RuntimeError(f"Model not found: {model_name}")
                    continue
                r.raise_for_status()
                data = r.json()
                latency = time.time() - start
                response = ""
                if isinstance(data, dict):
                    response = data.get("response") or data.get("content") or data.get("text") or ""
                else:
                    response = str(data)
                logger.info("LLAMA RESP len={} latency={:.3f}s model={}", len(response or ""), latency, model_name)
                return {"response": response, "latency_s": latency, "raw": data, "model": model_name}
            except Exception as e:
                last_error = e
                logger.exception("Ollama request failed for model=%s", model_name)
                # Try next model if available
                continue

    # If we exhausted all models
    raise OllamaError(str(last_error) if last_error else "Unknown error calling Ollama")

if __name__ == "__main__":
    # Quick local smoke test
    try:
        print("Running local smoke test...")
        out = query_llama("Write a one-line friendly welcome message for a support chat.")
        print(out["response"])
    except OllamaError as e:
        print("OllamaError:", e)
