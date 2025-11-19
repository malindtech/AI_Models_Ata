# scripts/test_validation_standalone.py
"""
Standalone validation test - tests ValidationRules without backend
"""
import sys
from pathlib import Path

# Add ui directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "ui"))

print("Testing ValidationRules...")
print("=" * 70)

try:
    from review_app import ValidationRules
    print("✅ Successfully imported ValidationRules")
except Exception as e:
    print(f"❌ Failed to import: {e}")
    sys.exit(1)

# Test cases
test_cases = [
    {
        "name": "Valid content",
        "headline": "Great Product Features",
        "body": "This is a comprehensive description of our amazing product with all the features you need.",
        "expected_valid": True
    },
    {
        "name": "Empty content",
        "headline": "",
        "body": "",
        "expected_valid": False
    },
    {
        "name": "Too short",
        "headline": "Hi",
        "body": "Short",
        "expected_valid": False
    },
    {
        "name": "Profanity detected",
        "headline": "This is stupid",
        "body": "I hate this damn product",
        "expected_valid": False
    },
    {
        "name": "Suspicious patterns",
        "headline": "Click here now!",
        "body": "Act now! 100% free! Guaranteed results!",
        "expected_valid": False
    }
]

passed = 0
failed = 0

for idx, test in enumerate(test_cases, 1):
    print(f"\nTest {idx}/{len(test_cases)}: {test['name']}")
    
    result = ValidationRules.validate_all(test['headline'], test['body'])
    
    if result['valid'] == test['expected_valid']:
        print(f"  ✅ PASSED - valid={result['valid']}")
        if result['issues']:
            print(f"     Issues: {', '.join(result['issues'])}")
        passed += 1
    else:
        print(f"  ❌ FAILED - Expected {test['expected_valid']}, got {result['valid']}")
        failed += 1

print("\n" + "=" * 70)
print(f"Results: {passed}/{len(test_cases)} tests passed")

if passed == len(test_cases):
    print("🎉 All validation tests passed!")
    sys.exit(0)
else:
    print(f"⚠️  {failed} test(s) failed")
    sys.exit(1)
