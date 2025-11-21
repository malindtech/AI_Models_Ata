"""Quick test of production improvements"""
import requests
import json

BASE_URL = "http://localhost:8001"

print("=" * 60)
print("Testing Production Improvements")
print("=" * 60)

# Test 1: Multi-turn conversation with order number
print("\n[Test 1] Multi-turn conversation")
print("-" * 40)

history = []

# Turn 1: Initial complaint
msg1 = "My package is late"
print(f"User: {msg1}")

resp1 = requests.post(f"{BASE_URL}/v1/generate/reply?async_mode=false", json={
    "message": msg1,
    "conversation_history": history
})

if resp1.status_code == 200:
    reply1 = resp1.json()['reply']
    print(f"Bot:  {reply1}\n")
    history.append({"role": "user", "message": msg1})
    history.append({"role": "assistant", "message": reply1})
else:
    print(f"ERROR: {resp1.status_code} - {resp1.text}")
    exit(1)

# Turn 2: Provide order number
msg2 = "My order number is ABC-12345"
print(f"User: {msg2}")

resp2 = requests.post(f"{BASE_URL}/v1/generate/reply?async_mode=false", json={
    "message": msg2,
    "conversation_history": history
})

if resp2.status_code == 200:
    reply2 = resp2.json()['reply']
    print(f"Bot:  {reply2}\n")
    
    # Verify bot acknowledged order number
    if "ABC-12345" in reply2 or "abc-12345" in reply2.lower():
        print("✅ Bot acknowledged order number correctly")
    else:
        print("⚠️  Bot may not have acknowledged order number")
        print(f"    Reply was: {reply2}")
else:
    print(f"ERROR: {resp2.status_code} - {resp2.text}")

print("\n" + "=" * 60)
print("Test completed!")
print("=" * 60)
