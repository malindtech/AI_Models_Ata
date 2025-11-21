import requests
import json

# Test 1: Order with "Unknown - system offline" (ORD-10003)
print("=" * 70)
print("TEST 1: Order ORD-10003 (Processing, Unknown delivery)")
print("=" * 70)

response1 = requests.post(
    'http://localhost:8000/v1/generate/reply?async_mode=false',
    json={'message': 'Where is my order ORD-10003?', 'conversation_id': 'test_sync_1'}
)

print(f"\nStatus Code: {response1.status_code}")

if response1.status_code == 200:
    data = response1.json()
    reply = data.get('response', {}).get('reply', 'No reply')
    next_steps = data.get('response', {}).get('next_steps', 'N/A')
    
    print("\n📧 AGENT REPLY:")
    print("-" * 70)
    print(reply)
    print("-" * 70)
    
    print("\n📋 NEXT STEPS:")
    print(next_steps)
    
    # Validation
    print("\n🔍 ANTI-HALLUCINATION VALIDATION:")
    print("-" * 70)
    
    checks = []
    
    # Check 1: Acknowledges limited tracking
    if "don't have access to live" in reply.lower() or "don't have live" in reply.lower():
        checks.append("✅ Acknowledges no live tracking access")
    elif "unknown" in reply.lower() and "system offline" in reply.lower():
        checks.append("✅ Mentions 'Unknown - system offline'")
    else:
        checks.append("⚠️  Should acknowledge limited tracking")
    
    # Check 2: No specific delivery days
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    if any(day in reply.lower() for day in days):
        checks.append("❌ HALLUCINATION: Invented specific delivery day")
    else:
        checks.append("✅ No invented delivery dates")
    
    # Check 3: No fake tracking numbers
    if 'TRK' in reply and 'TRK' not in data.get('database_context', ''):
        checks.append("❌ HALLUCINATION: Invented tracking number")
    else:
        checks.append("✅ No invented tracking numbers")
    
    # Check 4: Mentions typical timeframe
    if "3-5" in reply or "typical" in reply.lower() or "usually" in reply.lower():
        checks.append("✅ Provides general timeframe expectations")
    else:
        checks.append("⚠️  Could mention typical processing time")
    
    for check in checks:
        print(check)
    
    print("-" * 70)
else:
    print(f"❌ Error: {response1.status_code}")
    print(response1.text)

print("\n" + "=" * 70)
print("TEST 2: Order ORD-10001 (Delivered with actual date)")
print("=" * 70)

response2 = requests.post(
    'http://localhost:8000/v1/generate/reply?async_mode=false',
    json={'message': 'Where is my order ORD-10001?', 'conversation_id': 'test_sync_2'}
)

print(f"\nStatus Code: {response2.status_code}")

if response2.status_code == 200:
    data = response2.json()
    reply = data.get('response', {}).get('reply', 'No reply')
    
    print("\n📧 AGENT REPLY:")
    print("-" * 70)
    print(reply)
    print("-" * 70)
    
    print("\n🔍 DATA GROUNDING VALIDATION:")
    print("-" * 70)
    
    checks = []
    
    # Check 1: Mentions delivered status
    if "delivered" in reply.lower():
        checks.append("✅ Confirms delivered status")
    else:
        checks.append("❌ Should mention delivered status")
    
    # Check 2: Includes actual delivery date
    if "november 4" in reply.lower() or "nov 4" in reply.lower() or "2024-11-04" in reply:
        checks.append("✅ Provides exact delivery date (Nov 4)")
    else:
        checks.append("⚠️  Should include delivery date (Nov 4, 2024)")
    
    # Check 3: Includes tracking number
    if "TRK1234567890" in reply:
        checks.append("✅ Provides exact tracking number")
    else:
        checks.append("⚠️  Could include tracking number")
    
    # Check 4: Mentions carrier
    if "fedex" in reply.lower():
        checks.append("✅ Mentions carrier (FedEx)")
    else:
        checks.append("⚠️  Could mention carrier")
    
    for check in checks:
        print(check)
    
    print("-" * 70)
else:
    print(f"❌ Error: {response2.status_code}")
    print(response2.text)

print("\n" + "=" * 70)
print("✅ Production-Ready Testing Complete!")
print("=" * 70)
