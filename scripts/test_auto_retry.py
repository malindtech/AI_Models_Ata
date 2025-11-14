# scripts/test_auto_retry.py
"""
Demonstrate auto-retry feature when validation fails
Shows how the system automatically regenerates content
"""
import sys
sys.path.insert(0, 'D:/Malind Tech/AI_Models_Ata')

from backend.celery_tasks import generate_reply_task

print("\n" + "="*70)
print("AUTO-RETRY DEMONSTRATION")
print("="*70)

print("\n📖 How Auto-Retry Works:")
print("   1. Generate reply")
print("   2. Validate reply")
print("   3. If fails → Automatically regenerate (up to 3 total attempts)")
print("   4. Return first valid result OR final failure")

print("\n" + "="*70)
print("SCENARIO 1: Normal Case (Should Pass on First Try)")
print("="*70)

message1 = "I need help with my order"
print(f"\nMessage: \"{message1}\"")
print("Expected: Professional reply, passes validation on attempt 1")

# Note: This runs the task synchronously for testing
# In production, use .delay() for async
result1 = generate_reply_task(message1, max_validation_retries=2)

print(f"\n✅ Result Status: {result1['status']}")
print(f"🔄 Generation Attempts: {result1.get('generation_attempts', 1)}")

if result1['status'] == 'success':
    print(f"💬 Reply: {result1['reply'][:100]}...")
    print(f"✅ Validation: {result1['validation']['valid']}")
else:
    print(f"❌ Failed: {result1.get('error')}")

print("\n" + "="*70)
print("SCENARIO 2: Understanding Retry Logic")
print("="*70)

print("\n📊 What happens with auto-retry:")
print("""
Attempt 1: Generate → Validate
           ├─ PASS → Return success ✅
           └─ FAIL → Try again
                      ↓
Attempt 2: Generate → Validate
           ├─ PASS → Return success ✅
           └─ FAIL → Try again
                      ↓
Attempt 3: Generate → Validate
           ├─ PASS → Return success ✅
           └─ FAIL → Return failure ❌ (exhausted retries)
""")

print("\n💡 Key Points:")
print("   • Intent classification happens ONCE (no need to reclassify)")
print("   • Each attempt generates a NEW reply")
print("   • Stops as soon as ONE passes validation")
print("   • Maximum attempts = 1 + max_validation_retries (default: 3 total)")

print("\n" + "="*70)
print("SCENARIO 3: Check Attempt Details")
print("="*70)

if 'attempt_details' in result1:
    print(f"\n📝 Generation Attempt History:")
    for attempt in result1['attempt_details']:
        print(f"\n   Attempt {attempt['attempt']}:")
        print(f"   - Reply: {attempt['reply'][:60]}...")
        print(f"   - Validation: {attempt['validation_result']}")
        print(f"   - Latency: {attempt['generation_latency_s']:.2f}s")
        if attempt['validation_result'] == 'FAILED':
            print(f"   - Reason: {attempt['failure_reason']}")

print("\n" + "="*70)
print("CONFIGURATION OPTIONS")
print("="*70)

print("""
You can control retry behavior when submitting tasks:

Python API:
-----------
# Default: 2 retries (3 total attempts)
task = generate_reply_task.delay(message)

# Custom: 5 retries (6 total attempts)
task = generate_reply_task.delay(message, max_validation_retries=5)

# No retries (1 attempt only)
task = generate_reply_task.delay(message, max_validation_retries=0)


REST API (main.py needs update):
---------------------------------
POST /v1/generate/reply
{
  "message": "Help me",
  "max_validation_retries": 2
}


Environment Variable (future):
-------------------------------
MAX_VALIDATION_RETRIES=3
""")

print("\n" + "="*70)
print("COST CONSIDERATIONS")
print("="*70)

print("""
⚠️  Each retry calls the LLM again!

Example costs:
--------------
• 1st attempt fails → 1 LLM call wasted
• 2nd attempt fails → 2 LLM calls wasted  
• 3rd attempt passes → 3 LLM calls total

Recommendations:
----------------
✅ Use 2-3 retries for production (default)
✅ Monitor validation failure rates
✅ If >50% fail, improve prompts instead of retrying
⚠️  Don't set too high (e.g., 10 retries)
""")

print("\n" + "="*70)
print("WHEN TO USE AUTO-RETRY")
print("="*70)

print("""
✅ Good Use Cases:
   • Occasional validation failures (< 10%)
   • Temporary forbidden phrase issues
   • Edge cases in toxicity detection
   • Better UX (transparent to user)

❌ Bad Use Cases:
   • Prompt consistently generates bad content (> 50%)
   • Forbidden phrase list too restrictive
   • Cost is a major concern
   → Fix root cause instead!
""")

print("\n" + "="*70)
print("✅ AUTO-RETRY FEATURE EXPLAINED")
print("="*70)

print("""
Summary:
--------
✅ Automatically regenerates if validation fails
✅ Configurable retry limit (default: 2)
✅ Tracks all attempts for debugging
✅ Returns detailed failure info if all attempts fail
✅ Better UX - user doesn't need to retry manually

Next Steps:
-----------
1. Test with real API (needs FastAPI running)
2. Monitor retry rates in production
3. Adjust retry limit based on failure patterns
4. Consider prompt improvements if failures are common
""")

print("\n" + "="*70)
