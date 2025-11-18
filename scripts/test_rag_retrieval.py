"""
Day 5: RAG Retrieval Validation Script
Tests the /v1/retrieve endpoint with various queries
"""

import requests
import json
from typing import List, Dict
from loguru import logger

BASE_URL = "http://localhost:8000"

# Test cases covering different scenarios
TEST_CASES = [
    {
        "name": "Product Search - Specific Collection",
        "query": "laptop with good battery life",
        "collection": "products",
        "top_k": 3,
        "expected_min_results": 1
    },
    {
        "name": "Support Query - Customer Service Issue",
        "query": "order not delivered and need refund",
        "collection": "support",
        "top_k": 5,
        "expected_min_results": 2
    },
    {
        "name": "Cross-Collection Search - General",
        "query": "smartphone reviews and recommendations",
        "collection": None,  # Search all collections
        "top_k": 5,
        "expected_min_results": 3
    },
    {
        "name": "Blog Content Search",
        "query": "technology trends and innovation",
        "collection": "blogs",
        "top_k": 3,
        "expected_min_results": 1
    },
    {
        "name": "Social Media Content",
        "query": "customer testimonials and feedback",
        "collection": "social",
        "top_k": 3,
        "expected_min_results": 1
    }
]

def test_retrieve(query: str, collection: str = None, top_k: int = 5) -> Dict:
    """Test the /v1/retrieve endpoint"""
    endpoint = f"{BASE_URL}/v1/retrieve"
    
    payload = {
        "query": query,
        "top_k": top_k
    }
    
    if collection:
        payload["collection"] = collection
    
    logger.info(f"🔍 Testing query: '{query}' | Collection: {collection or 'ALL'} | Top-K: {top_k}")
    
    try:
        response = requests.post(endpoint, json=payload, timeout=240)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"✅ Retrieved {data['num_results']} results in {data['latency_ms']:.2f}ms")
        
        return data
    
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request failed: {e}")
        return None

def display_results(results: Dict):
    """Display retrieval results in a readable format"""
    if not results or not results.get('results'):
        logger.warning("No results to display")
        return
    
    print("\n" + "="*80)
    print(f"Query: {results['query']}")
    print(f"Collection: {results['collection'] or 'ALL COLLECTIONS'}")
    print(f"Results: {results['num_results']} | Latency: {results['latency_ms']:.2f}ms")
    print("="*80)
    
    for idx, doc in enumerate(results['results'], 1):
        print(f"\n📄 Result #{idx} (Collection: {doc['collection']})")
        print(f"   Distance: {doc['distance']:.4f}")
        print(f"   ID: {doc['id']}")
        
        # Display text preview (first 200 chars)
        text_preview = doc['text'][:200] + "..." if len(doc['text']) > 200 else doc['text']
        print(f"   Text: {text_preview}")
        
        # Display metadata if available
        if doc.get('metadata'):
            print(f"   Metadata: {json.dumps(doc['metadata'], indent=6)}")
    
    print("\n" + "="*80 + "\n")

def run_test_suite():
    """Run all test cases"""
    print("\n" + "="*80)
    print("  DAY 5: RAG RETRIEVAL VALIDATION")
    print("="*80 + "\n")
    
    # Check server health
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5).json()
        logger.info(f"Server Health: {health}")
        
        if not health.get("vector_db"):
            logger.error("❌ Vector DB not available on server!")
            return
    
    except Exception as e:
        logger.error(f"❌ Server not reachable: {e}")
        return
    
    # Run test cases
    passed = 0
    failed = 0
    
    for idx, test in enumerate(TEST_CASES, 1):
        print(f"\n{'='*80}")
        print(f"TEST CASE #{idx}: {test['name']}")
        print(f"{'='*80}")
        
        results = test_retrieve(
            query=test['query'],
            collection=test['collection'],
            top_k=test['top_k']
        )
        
        if results:
            display_results(results)
            
            # Validate results
            num_results = results.get('num_results', 0)
            expected_min = test['expected_min_results']
            
            if num_results >= expected_min:
                logger.info(f"✅ Test passed: {num_results} >= {expected_min} results")
                passed += 1
            else:
                logger.warning(f"⚠️ Test passed but fewer results than expected: {num_results} < {expected_min}")
                passed += 1
        else:
            logger.error(f"❌ Test failed: No results returned")
            failed += 1
    
    # Summary
    print("\n" + "="*80)
    print("  TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {len(TEST_CASES)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(TEST_CASES)*100):.1f}%")
    print("="*80 + "\n")

if __name__ == "__main__":
    run_test_suite()
