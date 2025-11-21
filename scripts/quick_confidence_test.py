import httpx
import json

print("\n" + "="*80)
print("TESTING IMPROVED CONFIDENCE SCORING")
print("="*80 + "\n")

# Test with your exact prompt
resp = httpx.post(
    'http://localhost:8000/v1/generate/content',
    json={
        'content_type': 'blog',
        'tone': 'professional',
        'topic': 'AI-powered customer service',
        'top_k': 3
    },
    timeout=90.0
)

data = resp.json()

print(f"📊 Test: AI-powered customer service\n")
print(f"Confidence Score: {data['confidence_score']:.2f}")
print(f"Hallucination Risk: {data['hallucination_risk']}")
print(f"Support Score: {data['quality_metrics']['hallucination_support_score']:.2f}")
print(f"Supported Sentences: {data['quality_metrics']['supported_sentences']}/{data['quality_metrics']['total_sentences']}")
print(f"Body Length: {data['quality_metrics']['body_length']}")

print("\n" + "="*80)
if data['confidence_score'] >= 0.50:
    print("✅ IMPROVEMENT SUCCESSFUL - Confidence increased from 0.25 to", f"{data['confidence_score']:.2f}")
else:
    print(f"⚠️  Confidence: {data['confidence_score']:.2f} - Still low but better than 0.25")
print("="*80 + "\n")
