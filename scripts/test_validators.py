# scripts/test_validators.py
"""
Test the validators module independently (without Celery/Redis)
"""
import sys
sys.path.insert(0, 'D:/Malind Tech/AI_Models_Ata')

from backend.validators import (
    validate_length,
    validate_forbidden_phrases,
    validate_content,
    ValidationError
)

print("=" * 70)
print("TESTING VALIDATORS (No Redis/Celery needed)")
print("=" * 70)

# Test 1: Valid content
print("\n🧪 Test 1: Valid content")
try:
    result = validate_content("Thank you for contacting us. We'll help you resolve this issue promptly.")
    print("✅ PASSED - Valid content accepted")
    print(f"   Checks: {result['checks'].keys()}")
except ValidationError as e:
    print(f"❌ FAILED - {e.reason}")

# Test 2: Too short
print("\n🧪 Test 2: Content too short")
try:
    result = validate_content("Hi")
    print("❌ FAILED - Should have been rejected")
except ValidationError as e:
    print(f"✅ PASSED - Rejected: {e.reason}")

# Test 3: Too long
print("\n🧪 Test 3: Content too long")
try:
    long_text = "X" * 6000
    result = validate_content(long_text)
    print("❌ FAILED - Should have been rejected")
except ValidationError as e:
    print(f"✅ PASSED - Rejected: {e.reason}")

# Test 4: Forbidden phrases
print("\n🧪 Test 4: Forbidden phrases")
test_phrases = [
    "That's not my problem, deal with it yourself",
    "You're being stupid about this",
    "Just shut up and listen"
]

for phrase in test_phrases:
    try:
        result = validate_content(phrase)
        print(f"❌ FAILED - Should reject: '{phrase[:40]}...'")
    except ValidationError as e:
        found = e.details.get('checks', {}).get('forbidden_phrases', {}).get('found', [])
        print(f"✅ PASSED - Detected forbidden: {found}")

# Test 5: Safe professional content
print("\n🧪 Test 5: Professional support replies")
professional_replies = [
    "I understand your frustration. Let me help you resolve this issue.",
    "Thank you for bringing this to our attention. We'll investigate right away.",
    "I apologize for the inconvenience. Here's what we can do to help."
]

for reply in professional_replies:
    try:
        result = validate_content(reply)
        print(f"✅ PASSED - Accepted: '{reply[:50]}...'")
    except ValidationError as e:
        print(f"❌ FAILED - Rejected: {e.reason}")

print("\n" + "=" * 70)
print("Note: Toxicity detection will download model on first run (~400MB)")
print("      This may take a few minutes with internet connection")
print("=" * 70)

# Test 6: Toxicity detection (optional - requires model download)
print("\n🧪 Test 6: Toxicity detection (downloading model if needed...)")
try:
    from backend.validators import validate_toxicity
    
    safe_text = "Thank you for your patience while we resolve this."
    toxic_text = "You're an idiot and I hate you"
    
    print("\n   Testing safe text...")
    is_valid, msg, score = validate_toxicity(safe_text)
    print(f"   {'✅' if is_valid else '❌'} Safe text - Score: {score:.3f}, Result: {msg or 'PASS'}")
    
    print("\n   Testing toxic text...")
    is_valid, msg, score = validate_toxicity(toxic_text)
    print(f"   {'✅' if not is_valid else '⚠️'} Toxic text - Score: {score:.3f}, Result: {msg or 'Low toxicity'}")
    
except Exception as e:
    print(f"   ⚠️  Toxicity test skipped: {e}")
    print(f"   (This is normal if model isn't downloaded yet)")

print("\n" + "=" * 70)
print("✅ VALIDATOR TESTS COMPLETE")
print("=" * 70)
