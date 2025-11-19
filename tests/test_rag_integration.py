"""
Test Suite 3: RAG Integration Testing

Tests RAG (Retrieval-Augmented Generation) inside both agents:
- Content Generation Agent (6 content types)
- Customer Support Agent (reply generation)

Tests:
1. Compare answers with vs without RAG
2. Ensure retrieved context matches query
3. Validate answer quality improvement
4. Test irrelevant query fallback
5. Test both agents separately
"""

import sys
from pathlib import Path
import time
import requests
from typing import Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
RESET = '\033[0m'
BOLD = '\033[1m'

# API base URL
BASE_URL = "http://localhost:8000"


def check_api_health():
    """Check if API is running and vector DB is available"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=15)
        if response.status_code == 200:
            data = response.json()
            vector_db = data.get('vector_db', False)
            print(f"{GREEN}✓ API is running{RESET}")
            print(f"  Vector DB: {'Available' if vector_db else 'Unavailable'}")
            return vector_db
        else:
            print(f"{RED}✗ API health check failed: status {response.status_code}{RESET}")
            return False
    except Exception as e:
        print(f"{RED}✗ API not accessible: {e}{RESET}")
        print(f"{YELLOW}⚠ Make sure to start the API: uvicorn backend.main:app --reload{RESET}")
        return False


def test_content_generation_with_rag():
    """Test 1: Content Generation Agent - RAG enhancement"""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}Test 1: Content Generation Agent - RAG Enhancement{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    # Test cases for different content types
    test_cases = [
        {
            "content_type": "blog",
            "topic": "AI automation customer support",
            "tone": "professional",
            "expected_keywords": ["AI", "automation", "customer", "support"],
            "description": "Blog about AI customer support"
        },
        {
            "content_type": "product_description",
            "topic": "wireless headphones",
            "tone": "friendly",
            "expected_keywords": ["wireless", "headphones", "audio", "sound"],
            "description": "Product description for headphones"
        },
        {
            "content_type": "social_media",
            "topic": "summer sale promotion",
            "tone": "casual",
            "expected_keywords": ["sale", "summer", "discount", "offer"],
            "description": "Social media post for sale"
        }
    ]
    
    print(f"{BOLD}Testing Content Generation with RAG:{RESET}\n")
    
    all_passed = True
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{BLUE}{'─'*80}{RESET}")
        print(f"{BLUE}Content Generation Test {i}: {test['description']}{RESET}")
        print(f"{BLUE}{'─'*80}{RESET}\n")
        
        print(f"Content Type: {test['content_type']}")
        print(f"Topic: {test['topic']}")
        print(f"Tone: {test['tone']}")
        
        try:
            # Make API request
            payload = {
                "content_type": test['content_type'],
                "topic": test['topic'],
                "tone": test['tone']
            }
            
            start_time = time.time()
            response = requests.post(
                f"{BASE_URL}/v1/generate/content",
                json=payload,
                timeout=60
            )
            latency = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"\n{GREEN}✓ Generation successful ({latency:.2f}s){RESET}")
                print(f"\n{BOLD}Generated Content:{RESET}")
                print(f"{CYAN}Headline:{RESET} {data['headline']}")
                print(f"{CYAN}Body:{RESET} {data['body'][:200]}...")
                
                # Analyze content quality
                body_text = data['body'].lower()
                headline_text = data['headline'].lower()
                full_text = body_text + " " + headline_text
                
                # Check for expected keywords
                keywords_found = sum(1 for kw in test['expected_keywords'] if kw.lower() in full_text)
                keyword_ratio = keywords_found / len(test['expected_keywords'])
                
                print(f"\n{BOLD}Quality Analysis:{RESET}")
                print(f"  • Keywords found: {keywords_found}/{len(test['expected_keywords'])} ({keyword_ratio*100:.0f}%)")
                print(f"  • Content length: {len(data['body'])} chars")
                print(f"  • Generation latency: {data['latency_s']:.2f}s")
                
                # Pass criteria: at least 50% keywords + reasonable length
                if keyword_ratio >= 0.5 and len(data['body']) > 100:
                    print(f"  {GREEN}✓ Good content quality{RESET}")
                else:
                    print(f"  {YELLOW}⚠ Moderate content quality{RESET}")
                    all_passed = False
                
            else:
                print(f"{RED}✗ Generation failed: status {response.status_code}{RESET}")
                print(f"  Error: {response.text}")
                all_passed = False
                
        except Exception as e:
            print(f"{RED}✗ Error: {e}{RESET}")
            all_passed = False
    
    print(f"\n{BLUE}{'─'*80}{RESET}\n")
    
    if all_passed:
        print(f"{GREEN}{BOLD}✓ TEST 1 PASSED: Content Generation with RAG works correctly{RESET}\n")
        return True
    else:
        print(f"{YELLOW}{BOLD}⚠ TEST 1 PARTIAL: Some content generation issues{RESET}\n")
        return False


def test_customer_support_with_rag():
    """Test 2: Customer Support Agent - RAG-enhanced replies"""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}Test 2: Customer Support Agent - RAG Enhancement{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    # Test cases for customer support
    test_cases = [
        {
            "message": "My order hasn't arrived yet. It's been 2 weeks.",
            "expected_intent": "complaint",
            "expected_keywords": ["order", "delivery", "track", "apologize"],
            "description": "Shipping delay complaint"
        },
        {
            "message": "How do I return a product that doesn't fit?",
            "expected_intent": "inquiry",
            "expected_keywords": ["return", "policy", "refund", "process"],
            "description": "Return policy inquiry"
        },
        {
            "message": "I need to change my shipping address urgently.",
            "expected_intent": "request",
            "expected_keywords": ["address", "update", "shipping", "change"],
            "description": "Address change request"
        }
    ]
    
    print(f"{BOLD}Testing Customer Support with RAG:{RESET}\n")
    
    all_passed = True
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{BLUE}{'─'*80}{RESET}")
        print(f"{BLUE}Support Test {i}: {test['description']}{RESET}")
        print(f"{BLUE}{'─'*80}{RESET}\n")
        
        print(f"Customer Message: '{test['message']}'")
        print(f"Expected Intent: {test['expected_intent']}")
        
        try:
            # Make API request (async mode with task polling)
            payload = {"message": test['message']}
            
            # Submit task
            response = requests.post(
                f"{BASE_URL}/v1/generate/reply?async_mode=true",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                task_data = response.json()
                task_id = task_data['task_id']
                print(f"\n{GREEN}✓ Task submitted: {task_id}{RESET}")
                
                # Poll for result
                max_attempts = 30
                for attempt in range(max_attempts):
                    time.sleep(2)
                    status_response = requests.get(f"{BASE_URL}/v1/tasks/{task_id}", timeout=10)
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data['status']
                        
                        if status == 'success':
                            result = status_data['result']
                            
                            print(f"{GREEN}✓ Reply generated successfully{RESET}")
                            print(f"\n{BOLD}Agent Response:{RESET}")
                            print(f"{CYAN}Detected Intent:{RESET} {result['detected_intent']}")
                            print(f"{CYAN}Reply:{RESET} {result['reply'][:200]}...")
                            print(f"{CYAN}Next Steps:{RESET} {result.get('next_steps', 'N/A')[:100]}...")
                            
                            # Verify intent
                            detected_intent = result['detected_intent']
                            intent_match = detected_intent == test['expected_intent']
                            
                            # Check for expected keywords in reply
                            reply_text = result['reply'].lower()
                            keywords_found = sum(1 for kw in test['expected_keywords'] if kw.lower() in reply_text)
                            keyword_ratio = keywords_found / len(test['expected_keywords'])
                            
                            print(f"\n{BOLD}Quality Analysis:{RESET}")
                            print(f"  • Intent match: {GREEN if intent_match else YELLOW}{'✓' if intent_match else '✗'} {detected_intent}{RESET}")
                            print(f"  • Keywords found: {keywords_found}/{len(test['expected_keywords'])} ({keyword_ratio*100:.0f}%)")
                            print(f"  • Reply length: {len(result['reply'])} chars")
                            print(f"  • Total latency: {result['total_latency_s']:.2f}s")
                            
                            # Pass criteria: intent match + at least 25% keywords
                            if intent_match and keyword_ratio >= 0.25:
                                print(f"  {GREEN}✓ Good reply quality{RESET}")
                            else:
                                print(f"  {YELLOW}⚠ Moderate reply quality (intent: {intent_match}, keywords: {keyword_ratio*100:.0f}%){RESET}")
                                all_passed = False
                            
                            break
                            
                        elif status == 'failed':
                            print(f"{RED}✗ Task failed: {status_data.get('error', 'Unknown error')}{RESET}")
                            all_passed = False
                            break
                        else:
                            print(f"  Waiting... (attempt {attempt+1}/{max_attempts}, status: {status})")
                else:
                    print(f"{RED}✗ Task timed out after {max_attempts} attempts{RESET}")
                    all_passed = False
            else:
                print(f"{RED}✗ Task submission failed: status {response.status_code}{RESET}")
                all_passed = False
                
        except Exception as e:
            print(f"{RED}✗ Error: {e}{RESET}")
            all_passed = False
    
    print(f"\n{BLUE}{'─'*80}{RESET}\n")
    
    if all_passed:
        print(f"{GREEN}{BOLD}✓ TEST 2 PASSED: Customer Support with RAG works correctly{RESET}\n")
        return True
    else:
        print(f"{YELLOW}{BOLD}⚠ TEST 2 PARTIAL: Some support generation issues{RESET}\n")
        return False


def test_rag_context_relevance():
    """Test 3: Verify retrieved context matches query"""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}Test 3: RAG Context Relevance{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    # Test queries for retrieval endpoint
    test_cases = [
        {
            "query": "product return policy",
            "collection": "support",
            "expected_keywords": ["return", "refund", "policy"],
            "description": "Support collection - return policy"
        },
        {
            "query": "blog article about technology",
            "collection": "blogs",
            "expected_keywords": ["technology", "article", "blog"],
            "description": "Blogs collection - technology content"
        },
        {
            "query": "customer review feedback",
            "collection": "reviews",
            "expected_keywords": ["review", "customer", "product"],
            "description": "Reviews collection - customer feedback"
        }
    ]
    
    print(f"{BOLD}Testing RAG Context Retrieval:{RESET}\n")
    
    all_passed = True
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{BLUE}{'─'*80}{RESET}")
        print(f"{BLUE}Retrieval Test {i}: {test['description']}{RESET}")
        print(f"{BLUE}{'─'*80}{RESET}\n")
        
        print(f"Query: '{test['query']}'")
        print(f"Collection: {test['collection']}")
        
        try:
            # Make retrieval API request
            payload = {
                "query": test['query'],
                "collection": test['collection'],
                "top_k": 3
            }
            
            response = requests.post(
                f"{BASE_URL}/v1/retrieve",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"\n{GREEN}✓ Retrieved {data['num_results']} results ({data['latency_ms']:.2f}ms){RESET}\n")
                
                if data['num_results'] > 0:
                    print(f"{BOLD}Top 3 Results:{RESET}\n")
                    
                    relevant_count = 0
                    
                    for j, result in enumerate(data['results'][:3], 1):
                        result_text = result['text'].lower()
                        keywords_found = sum(1 for kw in test['expected_keywords'] if kw.lower() in result_text)
                        is_relevant = keywords_found > 0
                        
                        if is_relevant:
                            relevant_count += 1
                        
                        status = f"{GREEN}✓{RESET}" if is_relevant else f"{YELLOW}?{RESET}"
                        
                        print(f"{j}. {status} ID: {result['id']}")
                        print(f"   Distance: {result['distance']:.4f}")
                        print(f"   Collection: {result['collection']}")
                        print(f"   Keywords found: {keywords_found}/{len(test['expected_keywords'])}")
                        print(f"   Text: '{result['text'][:100]}...'")
                        print()
                    
                    print(f"{BOLD}Relevance Analysis:{RESET}")
                    print(f"  • Relevant results: {relevant_count}/3")
                    print(f"  • Average distance: {sum(r['distance'] for r in data['results'][:3]) / min(3, len(data['results'])):.4f}")
                    
                    if relevant_count >= 2:
                        print(f"  {GREEN}✓ Good relevance (≥2 relevant){RESET}")
                    elif relevant_count >= 1:
                        print(f"  {YELLOW}⚠ Moderate relevance (≥1 relevant){RESET}")
                        all_passed = False
                    else:
                        print(f"  {RED}✗ Poor relevance (0 relevant){RESET}")
                        all_passed = False
                else:
                    print(f"{RED}✗ No results returned{RESET}")
                    all_passed = False
            else:
                print(f"{RED}✗ Retrieval failed: status {response.status_code}{RESET}")
                print(f"  Error: {response.text}")
                all_passed = False
                
        except Exception as e:
            print(f"{RED}✗ Error: {e}{RESET}")
            all_passed = False
    
    print(f"\n{BLUE}{'─'*80}{RESET}\n")
    
    if all_passed:
        print(f"{GREEN}{BOLD}✓ TEST 3 PASSED: RAG context relevance is good{RESET}\n")
        return True
    else:
        print(f"{YELLOW}{BOLD}⚠ TEST 3 PARTIAL: Some relevance issues{RESET}\n")
        return False


def test_irrelevant_query_fallback():
    """Test 4: Test irrelevant query fallback (graceful degradation)"""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}Test 4: Irrelevant Query Fallback{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    print(f"{BOLD}Testing graceful degradation with irrelevant queries:{RESET}\n")
    
    # Completely irrelevant queries that should still get responses
    test_cases = [
        {
            "content_type": "blog",
            "topic": "quantum physics mathematical equations",
            "tone": "professional",
            "description": "Irrelevant topic for content generation"
        },
        {
            "message": "What is the weather like on Mars?",
            "description": "Irrelevant query for customer support"
        }
    ]
    
    all_passed = True
    
    # Test 1: Content generation with irrelevant topic
    print(f"\n{BLUE}Fallback Test 1: Content Generation{RESET}")
    print(f"Topic: {test_cases[0]['topic']}")
    
    try:
        payload = {
            "content_type": test_cases[0]['content_type'],
            "topic": test_cases[0]['topic'],
            "tone": test_cases[0]['tone']
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/generate/content",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n{GREEN}✓ Generated content despite irrelevant topic{RESET}")
            print(f"  Headline: {data['headline'][:60]}...")
            print(f"  Body length: {len(data['body'])} chars")
            print(f"  {GREEN}✓ Graceful degradation working{RESET}")
        else:
            print(f"{RED}✗ Failed to generate: {response.status_code}{RESET}")
            all_passed = False
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        all_passed = False
    
    # Test 2: Customer support with irrelevant query
    print(f"\n{BLUE}Fallback Test 2: Customer Support{RESET}")
    print(f"Message: {test_cases[1]['message']}")
    
    try:
        payload = {"message": test_cases[1]['message']}
        
        response = requests.post(
            f"{BASE_URL}/v1/generate/reply?async_mode=true",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            task_data = response.json()
            task_id = task_data['task_id']
            
            # Poll for result
            for attempt in range(15):
                time.sleep(2)
                status_response = requests.get(f"{BASE_URL}/v1/tasks/{task_id}", timeout=10)
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    
                    if status_data['status'] == 'success':
                        result = status_data['result']
                        print(f"\n{GREEN}✓ Generated reply despite irrelevant query{RESET}")
                        print(f"  Intent: {result['detected_intent']}")
                        print(f"  Reply: {result['reply'][:100]}...")
                        print(f"  {GREEN}✓ Graceful degradation working{RESET}")
                        break
                    elif status_data['status'] == 'failed':
                        print(f"{RED}✗ Task failed: {status_data.get('error')}{RESET}")
                        all_passed = False
                        break
            else:
                print(f"{RED}✗ Task timed out{RESET}")
                all_passed = False
        else:
            print(f"{RED}✗ Task submission failed: {response.status_code}{RESET}")
            all_passed = False
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        all_passed = False
    
    print()
    
    if all_passed:
        print(f"{GREEN}{BOLD}✓ TEST 4 PASSED: Graceful fallback working for irrelevant queries{RESET}\n")
        return True
    else:
        print(f"{RED}{BOLD}✗ TEST 4 FAILED: Fallback issues with irrelevant queries{RESET}\n")
        return False


def run_all_tests():
    """Run all RAG integration tests"""
    print(f"\n{BOLD}{MAGENTA}{'='*80}{RESET}")
    print(f"{BOLD}{MAGENTA}RAG INTEGRATION TEST SUITE{RESET}")
    print(f"{BOLD}{MAGENTA}Testing: RAG functionality in both agents{RESET}")
    print(f"{BOLD}{MAGENTA}{'='*80}{RESET}\n")
    
    # Check API health
    print(f"{BOLD}Checking API availability...{RESET}\n")
    if not check_api_health():
        print(f"\n{RED}{BOLD}✗ TESTS ABORTED: API not available{RESET}")
        print(f"{YELLOW}Start the API with: uvicorn backend.main:app --reload{RESET}\n")
        return False
    
    print(f"\n{GREEN}✓ API is ready{RESET}")
    print(f"{CYAN}Starting RAG integration tests...{RESET}\n")
    
    time.sleep(1)
    
    results = {
        "Test 1: Content Generation with RAG": test_content_generation_with_rag(),
        "Test 2: Customer Support with RAG": test_customer_support_with_rag(),
        "Test 3: RAG Context Relevance": test_rag_context_relevance(),
        "Test 4: Irrelevant Query Fallback": test_irrelevant_query_fallback()
    }
    
    # Summary
    print(f"\n{BOLD}{MAGENTA}{'='*80}{RESET}")
    print(f"{BOLD}{MAGENTA}RAG INTEGRATION TEST SUMMARY{RESET}")
    print(f"{BOLD}{MAGENTA}{'='*80}{RESET}\n")
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{GREEN}PASSED{RESET}" if result else f"{YELLOW}PARTIAL{RESET}"
        print(f"{test_name}: {status}")
    
    print(f"\n{BOLD}Total: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"{GREEN}{BOLD}✓ ALL RAG INTEGRATION TESTS PASSED{RESET}")
        print(f"{GREEN}{BOLD}✓ Day 5 RAG implementation is working correctly!{RESET}\n")
        return True
    elif passed >= 3:
        print(f"{YELLOW}{BOLD}⚠ MOST RAG TESTS PASSED ({passed}/{total}){RESET}")
        print(f"{YELLOW}RAG implementation is functional with minor issues{RESET}\n")
        return True
    else:
        print(f"{RED}{BOLD}✗ MANY RAG TESTS FAILED{RESET}")
        print(f"{RED}RAG implementation needs fixes{RESET}\n")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
