# backend/validators.py
"""
Content validation module for safety checks
Includes: length validation, forbidden phrases, and toxicity detection
"""
import os
from typing import Dict, List, Tuple
from loguru import logger

# Validation configuration
MIN_CONTENT_LENGTH = int(os.getenv("MIN_CONTENT_LENGTH", "10"))
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "5000"))
TOXICITY_THRESHOLD = float(os.getenv("TOXICITY_THRESHOLD", "0.7"))

# Forbidden phrases/words list
FORBIDDEN_PHRASES = [
    # Profanity
    "damn", "hell", "shit", "fuck", "bitch", "ass",
    # Discriminatory
    "hate", "stupid", "idiot", "moron", "dumb",
    # Inappropriate for support
    "shut up", "go away", "leave me alone",
    "not my problem", "deal with it", "whatever",
    # Add more as needed
]


class ValidationError(Exception):
    """Raised when content fails validation"""
    def __init__(self, reason: str, details: dict = None):
        self.reason = reason
        self.details = details or {}
        super().__init__(reason)


def validate_length(text: str) -> Tuple[bool, str]:
    """
    Validate content length
    
    Args:
        text: Content to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    length = len(text)
    
    if length < MIN_CONTENT_LENGTH:
        return False, f"Content too short ({length} chars, minimum {MIN_CONTENT_LENGTH})"
    
    if length > MAX_CONTENT_LENGTH:
        return False, f"Content too long ({length} chars, maximum {MAX_CONTENT_LENGTH})"
    
    return True, ""


def validate_forbidden_phrases(text: str) -> Tuple[bool, str, List[str]]:
    """
    Check for forbidden words/phrases in content
    Uses word boundary matching to avoid false positives (e.g., "hello" won't match "hell")
    
    Args:
        text: Content to validate
        
    Returns:
        Tuple of (is_valid, error_message, found_phrases)
    """
    import re
    
    text_lower = text.lower()
    found_phrases = []
    
    for phrase in FORBIDDEN_PHRASES:
        # Use word boundaries to avoid false positives
        # \b matches word boundaries (start/end of word)
        pattern = r'\b' + re.escape(phrase.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found_phrases.append(phrase)
    
    if found_phrases:
        return False, f"Content contains forbidden phrases: {', '.join(found_phrases)}", found_phrases
    
    return True, "", []


def validate_toxicity(text: str) -> Tuple[bool, str, float]:
    """
    Check content for toxicity using transformer model
    
    Args:
        text: Content to validate
        
    Returns:
        Tuple of (is_valid, error_message, toxicity_score)
    """
    try:
        from transformers import pipeline
        
        # Initialize toxicity classifier (cached after first use)
        if not hasattr(validate_toxicity, "_classifier"):
            logger.info("Loading toxicity classifier model...")
            # Using unitary/toxic-bert model for toxicity detection
            validate_toxicity._classifier = pipeline(
                "text-classification",
                model="unitary/toxic-bert",
                device=-1,  # CPU
                truncation=True,
                max_length=512,
            )
            logger.info("Toxicity classifier loaded successfully")
        
        classifier = validate_toxicity._classifier
        
        # Truncate text if too long
        text_sample = text[:512] if len(text) > 512 else text
        
        # Get toxicity prediction
        result = classifier(text_sample)[0]
        
        # Result format: {"label": "toxic" or "non-toxic", "score": 0.0-1.0}
        is_toxic = result["label"].lower() == "toxic"
        score = result["score"] if is_toxic else (1.0 - result["score"])
        
        logger.info(f"Toxicity check: score={score:.3f}, threshold={TOXICITY_THRESHOLD}")
        
        if is_toxic and score >= TOXICITY_THRESHOLD:
            return False, f"Content flagged as toxic (score: {score:.2f})", score
        
        return True, "", score
        
    except Exception as e:
        logger.error(f"Toxicity validation error: {e}")
        # Fail open - if classifier fails, allow content through with warning
        logger.warning("Toxicity check failed, allowing content through")
        return True, f"Toxicity check unavailable: {e}", 0.0


def validate_content(text: str) -> Dict:
    """
    Run all validation checks on content
    
    Args:
        text: Content to validate
        
    Returns:
        Dict with validation results:
        {
            "valid": bool,
            "checks": {
                "length": {"passed": bool, "message": str},
                "forbidden_phrases": {"passed": bool, "message": str, "found": List[str]},
                "toxicity": {"passed": bool, "message": str, "score": float}
            },
            "failure_reason": str (if invalid)
        }
        
    Raises:
        ValidationError: If content fails any validation check
    """
    checks = {}
    
    # 1. Length validation
    length_valid, length_msg = validate_length(text)
    checks["length"] = {
        "passed": length_valid,
        "message": length_msg or "Length is valid"
    }
    
    if not length_valid:
        logger.warning(f"Length validation failed: {length_msg}")
        raise ValidationError("length_invalid", {"checks": checks})
    
    # 2. Forbidden phrases check
    phrases_valid, phrases_msg, found_phrases = validate_forbidden_phrases(text)
    checks["forbidden_phrases"] = {
        "passed": phrases_valid,
        "message": phrases_msg or "No forbidden phrases found",
        "found": found_phrases
    }
    
    if not phrases_valid:
        logger.warning(f"Forbidden phrases validation failed: {phrases_msg}")
        raise ValidationError("forbidden_phrases_detected", {"checks": checks})
    
    # 3. Toxicity check
    toxicity_valid, toxicity_msg, toxicity_score = validate_toxicity(text)
    checks["toxicity"] = {
        "passed": toxicity_valid,
        "message": toxicity_msg or "Content is non-toxic",
        "score": toxicity_score
    }
    
    if not toxicity_valid:
        logger.warning(f"Toxicity validation failed: {toxicity_msg}")
        raise ValidationError("toxic_content", {"checks": checks})
    
    # All checks passed
    logger.info("All validation checks passed")
    return {
        "valid": True,
        "checks": checks
    }


if __name__ == "__main__":
    # Quick test
    print("Testing validators...")
    
    # Test 1: Valid content
    try:
        result = validate_content("Thank you for contacting us. We'll help you resolve this issue.")
        print("✅ Valid content passed:", result["valid"])
    except ValidationError as e:
        print("❌ Valid content failed:", e.reason)
    
    # Test 2: Too short
    try:
        result = validate_content("Hi")
        print("❌ Short content should fail but passed")
    except ValidationError as e:
        print("✅ Short content rejected:", e.reason)
    
    # Test 3: Forbidden phrase
    try:
        result = validate_content("That's not my problem, deal with it yourself.")
        print("❌ Forbidden phrase should fail but passed")
    except ValidationError as e:
        print("✅ Forbidden phrase rejected:", e.reason)
    
    # Test 4: Toxic content (if model is available)
    try:
        result = validate_content("You're an idiot and I hate you.")
        print("❌ Toxic content should fail but passed")
    except ValidationError as e:
        print("✅ Toxic content rejected:", e.reason)
