import requests
import json
import time

# Test 1: Order with "Unknown - system offline" (ORD-10003)
print("=" * 60)
print("TEST 1: Order ORD-10003 (Processing, Unknown delivery)")
print("=" * 60)

response1 = requests.post(
    'http://localhost:8000/v1/generate/reply',
    json={'message': 'Where is my order ORD-10003?', 'conversation_id': 'test_offline_1'}
)
task_id_1 = response1.json().get('task_id')
print(f"✓ Task submitted: {task_id_1}")

# Wait for processing
print("⏳ Waiting 15 seconds for processing...")
time.sleep(15)

# Get result
result1 = requests.get(f'http://localhost:8000/v1/tasks/{task_id_1}').json()
print(f"\nStatus: {result1.get('status')}")

if result1.get('status') == 'completed' and result1.get('result'):
    reply = result1['result'].get('response', {}).get('reply', 'No reply')
    next_steps = result1['result'].get('response', {}).get('next_steps', 'N/A')
    
    print("\n📧 REPLY:")
    print(reply)
    print("\n📋 NEXT STEPS:")
    print(next_steps)
    
    # Check for anti-hallucination compliance
    print("\n🔍 VALIDATION:")
    if "Unknown - system offline" in reply or "don't have access to live" in reply.lower():
        print("✅ PASS: Agent acknowledges limited tracking access")
    elif "tuesday" in reply.lower() or "friday" in reply.lower():
        print("❌ FAIL: Agent hallucinated a specific day")
    else:
        print("⚠️  UNCLEAR: Check reply manually")
else:
    print(f"⚠️  Task not completed yet. Status: {result1.get('status')}")

print("\n" + "=" * 60)
print("TEST 2: Order ORD-10001 (Delivered with actual date)")
print("=" * 60)

response2 = requests.post(
    'http://localhost:8000/v1/generate/reply',
    json={'message': 'Where is my order ORD-10001?', 'conversation_id': 'test_delivered_1'}
)
task_id_2 = response2.json().get('task_id')
print(f"✓ Task submitted: {task_id_2}")

print("⏳ Waiting 15 seconds for processing...")
time.sleep(15)

result2 = requests.get(f'http://localhost:8000/v1/tasks/{task_id_2}').json()
print(f"\nStatus: {result2.get('status')}")

if result2.get('status') == 'completed' and result2.get('result'):
    reply = result2['result'].get('response', {}).get('reply', 'No reply')
    
    print("\n📧 REPLY:")
    print(reply)
    
    print("\n🔍 VALIDATION:")
    if "november 4" in reply.lower() or "nov 4" in reply.lower() or "2024-11-04" in reply:
        print("✅ PASS: Agent provided exact delivery date from database")
    else:
        print("⚠️  CHECK: Expected to see November 4, 2024")
else:
    print(f"⚠️  Task not completed yet. Status: {result2.get('status')}")

print("\n" + "=" * 60)
print("✅ Test complete!")
print("=" * 60)
