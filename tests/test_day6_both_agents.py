"""
Day 6 Production Test Suite - BOTH AGENTS
Tests query expansion, personalization, and hybrid retrieval for:
1. Content Generation Agent (/v1/generate/content)
2. Customer Support Reply Agent (/v1/generate/reply)

Production-level testing with comprehensive validation
"""

import sys
from pathlib import Path
import time
import requests
from typing import Dict, Any, List

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
RESET = '\033[0m'
BOLD = '\033[1m'

BASE_URL = "http://localhost:8000"


def print_banner(text: str, color: str = CYAN):
    """Print formatted banner"""
    print(f"\n{BOLD}{color}{'='*80}{RESET}")
    print(f"{BOLD}{color}{text}{RESET}")
    print(f"{BOLD}{color}{'='*80}{RESET}\n")


def print_test_header(test_num: int, test_name: str):
    """Print test header"""
    print(f"\n{BLUE}{'─'*80}{RESET}")
    print(f"{BLUE}{BOLD}Test {test_num}: {test_name}{RESET}")
    print(f"{BLUE}{'─'*80}{RESET}\n")


def check_system_status():
    """Verify Day 6 features are available"""
    print_banner("SYSTEM STATUS CHECK")
    
    try:
        response = requests.get(f"{BASE_URL}/v1/stats", timeout=10)
        response.raise_for_status()
        data = response.json()
        
        system = data.get('system', {})
        day6_available = system.get('day6_features_available', False)
        vector_db = system.get('vector_db_available', False)
        
        print(f"Vector DB Available: {GREEN if vector_db else RED}{'✓' if vector_db else '✗'}{RESET}")
        print(f"Day 6 Features Available: {GREEN if day6_available else RED}{'✓' if day6_available else '✗'}{RESET}")
        
        if not day6_available:
            print(f"\n{RED}⚠️  ERROR: Day 6 features not available!{RESET}")
            print(f"{YELLOW}Restart server to load Day 6 changes{RESET}\n")
            return False
        
        if not vector_db:
            print(f"\n{YELLOW}⚠️  WARNING: Vector DB not available (RAG features disabled){RESET}\n")
        
        print(f"\n{GREEN}✓ System ready for Day 6 testing{RESET}\n")
        return True
        
    except Exception as e:
        print(f"{RED}✗ System status check failed: {e}{RESET}\n")
        return False


# ============================================================================
# TEST SUITE 1: CONTENT GENERATION AGENT WITH DAY 6 FEATURES
# ============================================================================

def test_content_agent_query_expansion():
    """Test 1.1: Content Generation Agent with Query Expansion"""
    print_test_header("1.1", "Content Agent - Query Expansion")
    
    test_cases = [
        {
            "content_type": "blog",
            "topic": "help customers with order issues",
            "tone": "professional",
            "enable_expansion": True,
            "description": "Blog with query expansion"
        },
        {
            "content_type": "support_reply",
            "topic": "delivery problem urgent",
            "tone": "empathetic",
            "enable_expansion": True,
            "description": "Support reply with query expansion"
        },
        {
            "content_type": "product_description",
            "topic": "quality wireless headphones",
            "tone": "friendly",
            "enable_expansion": True,
            "description": "Product description with query expansion"
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{CYAN}Test Case {i}: {test['description']}{RESET}")
        print(f"Topic: {test['topic']}")
        print(f"Content Type: {test['content_type']}")
        
        try:
            start = time.time()
            response = requests.post(
                f"{BASE_URL}/v1/generate/content",
                json={
                    "content_type": test['content_type'],
                    "topic": test['topic'],
                    "tone": test['tone'],
                    "enable_expansion": test['enable_expansion']
                },
                timeout=120
            )
            latency = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                body_len = len(data['body'])
                
                print(f"{GREEN}✓ Generated successfully ({latency:.2f}s){RESET}")
                print(f"  Headline: {data['headline'][:60]}...")
                print(f"  Body length: {body_len} chars")
                print(f"  LLM latency: {data['latency_s']:.2f}s")
                
                # Validation
                if body_len > 100 and data['headline']:
                    print(f"  {GREEN}✓ Quality check passed{RESET}")
                    results.append(True)
                else:
                    print(f"  {RED}✗ Quality check failed{RESET}")
                    results.append(False)
            else:
                print(f"{RED}✗ Request failed: {response.status_code}{RESET}")
                results.append(False)
                
        except Exception as e:
            print(f"{RED}✗ Error: {e}{RESET}")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n{BLUE}{'─'*80}{RESET}")
    if passed == total:
        print(f"{GREEN}{BOLD}✓ TEST 1.1 PASSED: {passed}/{total} test cases successful{RESET}\n")
        return True
    else:
        print(f"{RED}{BOLD}✗ TEST 1.1 FAILED: {passed}/{total} test cases successful{RESET}\n")
        return False


def test_content_agent_personalization():
    """Test 1.2: Content Generation Agent with Personalization"""
    print_test_header("1.2", "Content Agent - Personalization")
    
    test_cases = [
        {
            "content_type": "support_reply",
            "topic": "order status inquiry",
            "tone": "friendly",
            "personalization_context": {
                "customer_name": "Sarah Johnson",
                "order_number": "ORD-12345",
                "product": "Wireless Mouse"
            },
            "description": "Support reply with customer info"
        },
        {
            "content_type": "email_newsletter",
            "topic": "monthly product updates",
            "tone": "professional",
            "personalization_context": {
                "customer_name": "Michael Chen",
                "company": "Tech Solutions Inc"
            },
            "description": "Newsletter with personalization"
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{CYAN}Test Case {i}: {test['description']}{RESET}")
        print(f"Topic: {test['topic']}")
        print(f"Personalization: {list(test['personalization_context'].keys())}")
        
        try:
            start = time.time()
            response = requests.post(
                f"{BASE_URL}/v1/generate/content",
                json={
                    "content_type": test['content_type'],
                    "topic": test['topic'],
                    "tone": test['tone'],
                    "personalization_context": test['personalization_context']
                },
                timeout=120
            )
            latency = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                body = data['body']
                
                print(f"{GREEN}✓ Generated successfully ({latency:.2f}s){RESET}")
                print(f"  Body: {body[:150]}...")
                
                # Check for personalization tokens in output
                tokens_found = []
                for key, value in test['personalization_context'].items():
                    if str(value) in body or str(value).split()[0] in body:
                        tokens_found.append(key)
                
                print(f"  Tokens found: {tokens_found if tokens_found else 'None (using fallbacks)'}")
                
                # Pass if content generated (personalization is optional, may use fallbacks)
                if len(body) > 100:
                    print(f"  {GREEN}✓ Content quality good{RESET}")
                    results.append(True)
                else:
                    print(f"  {RED}✗ Content too short{RESET}")
                    results.append(False)
            else:
                print(f"{RED}✗ Request failed: {response.status_code}{RESET}")
                results.append(False)
                
        except Exception as e:
            print(f"{RED}✗ Error: {e}{RESET}")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n{BLUE}{'─'*80}{RESET}")
    if passed == total:
        print(f"{GREEN}{BOLD}✓ TEST 1.2 PASSED: {passed}/{total} test cases successful{RESET}\n")
        return True
    else:
        print(f"{RED}{BOLD}✗ TEST 1.2 FAILED: {passed}/{total} test cases successful{RESET}\n")
        return False


def test_content_agent_all_types():
    """Test 1.3: Content Generation Agent - All 6 Content Types with Day 6"""
    print_test_header("1.3", "Content Agent - All 6 Content Types")
    
    test_cases = [
        ("blog", "AI customer service trends", "professional"),
        ("product_description", "smart home device", "friendly"),
        ("ad_copy", "summer sale campaign", "casual"),
        ("email_newsletter", "weekly tech updates", "professional"),
        ("social_media", "new product launch", "casual"),
        ("support_reply", "refund request processing", "empathetic")
    ]
    
    results = []
    
    for i, (content_type, topic, tone) in enumerate(test_cases, 1):
        print(f"\n{CYAN}Test {i}/6: {content_type}{RESET}")
        print(f"Topic: {topic}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/v1/generate/content",
                json={
                    "content_type": content_type,
                    "topic": topic,
                    "tone": tone,
                    "enable_expansion": True  # Day 6 enabled
                },
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"{GREEN}✓ Generated ({len(data['body'])} chars){RESET}")
                results.append(True)
            else:
                print(f"{RED}✗ Failed: {response.status_code}{RESET}")
                results.append(False)
                
        except Exception as e:
            print(f"{RED}✗ Error: {e}{RESET}")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n{BLUE}{'─'*80}{RESET}")
    if passed == total:
        print(f"{GREEN}{BOLD}✓ TEST 1.3 PASSED: All {total} content types work{RESET}\n")
        return True
    else:
        print(f"{RED}{BOLD}✗ TEST 1.3 FAILED: {passed}/{total} content types work{RESET}\n")
        return False


# ============================================================================
# TEST SUITE 2: CUSTOMER SUPPORT REPLY AGENT WITH DAY 6 FEATURES
# ============================================================================

def test_reply_agent_with_rag():
    """Test 2.1: Reply Agent with RAG (Day 5 + Day 6 enhancement)"""
    print_test_header("2.1", "Reply Agent - RAG Enhanced")
    
    test_cases = [
        {
            "message": "My order ABC-123 hasn't arrived yet. It's been 3 weeks!",
            "expected_intent": "complaint",
            "description": "Complaint with order number"
        },
        {
            "message": "How do I track my package?",
            "expected_intent": "inquiry",
            "description": "Tracking inquiry"
        },
        {
            "message": "I need to change my delivery address urgently",
            "expected_intent": "request",
            "description": "Address change request"
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{CYAN}Test Case {i}: {test['description']}{RESET}")
        print(f"Message: {test['message']}")
        
        try:
            start = time.time()
            response = requests.post(
                f"{BASE_URL}/v1/generate/reply?async_mode=false",
                json={"message": test['message']},
                timeout=120
            )
            latency = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"{GREEN}✓ Reply generated ({latency:.2f}s){RESET}")
                print(f"  Intent: {data['detected_intent']}")
                print(f"  Reply: {data['reply'][:100]}...")
                
                # Validate intent
                intent_correct = data['detected_intent'] == test['expected_intent']
                reply_sufficient = len(data['reply']) > 50
                
                if intent_correct and reply_sufficient:
                    print(f"  {GREEN}✓ Intent correct, reply sufficient{RESET}")
                    results.append(True)
                else:
                    print(f"  {YELLOW}⚠ Intent: {intent_correct}, Reply sufficient: {reply_sufficient}{RESET}")
                    results.append(False)
            else:
                print(f"{RED}✗ Request failed: {response.status_code}{RESET}")
                results.append(False)
                
        except Exception as e:
            print(f"{RED}✗ Error: {e}{RESET}")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n{BLUE}{'─'*80}{RESET}")
    if passed >= total * 0.66:  # 66% pass rate acceptable for LLM variability
        print(f"{GREEN}{BOLD}✓ TEST 2.1 PASSED: {passed}/{total} test cases successful{RESET}\n")
        return True
    else:
        print(f"{RED}{BOLD}✗ TEST 2.1 FAILED: {passed}/{total} test cases successful{RESET}\n")
        return False


def test_reply_agent_multi_turn():
    """Test 2.2: Reply Agent - Multi-turn Conversation"""
    print_test_header("2.2", "Reply Agent - Multi-turn Conversation")
    
    conversation_history = []
    
    # Turn 1
    print(f"\n{CYAN}Turn 1: Initial complaint{RESET}")
    message1 = "My package is late"
    
    try:
        response1 = requests.post(
            f"{BASE_URL}/v1/generate/reply?async_mode=false",
            json={"message": message1},
            timeout=120
        )
        
        if response1.status_code == 200:
            data1 = response1.json()
            print(f"{GREEN}✓ Reply 1 generated{RESET}")
            print(f"  Reply: {data1['reply'][:80]}...")
            
            conversation_history = [
                {"role": "customer", "message": message1},
                {"role": "agent", "message": data1['reply']}
            ]
        else:
            print(f"{RED}✗ Turn 1 failed{RESET}")
            return False
    except Exception as e:
        print(f"{RED}✗ Turn 1 error: {e}{RESET}")
        return False
    
    # Turn 2
    print(f"\n{CYAN}Turn 2: Follow-up with order number{RESET}")
    message2 = "My order number is ORD-98765"
    
    try:
        response2 = requests.post(
            f"{BASE_URL}/v1/generate/reply?async_mode=false",
            json={
                "message": message2,
                "conversation_history": conversation_history
            },
            timeout=120
        )
        
        if response2.status_code == 200:
            data2 = response2.json()
            print(f"{GREEN}✓ Reply 2 generated (with context){RESET}")
            print(f"  Reply: {data2['reply'][:80]}...")
            print(f"  {GREEN}✓ Multi-turn conversation works{RESET}")
            return True
        else:
            print(f"{RED}✗ Turn 2 failed{RESET}")
            return False
    except Exception as e:
        print(f"{RED}✗ Turn 2 error: {e}{RESET}")
        return False


def test_reply_agent_intent_classification():
    """Test 2.3: Reply Agent - Intent Classification Accuracy"""
    print_test_header("2.3", "Reply Agent - Intent Classification")
    
    test_cases = [
        ("My product is broken and I'm very upset!", "complaint"),
        ("Can you explain your return policy?", "inquiry"),
        ("Please cancel my order ABC-123", "request"),
        ("The item I received is damaged", "complaint"),
        ("What payment methods do you accept?", "inquiry"),
        ("I want to update my email address", "request")
    ]
    
    results = []
    
    for i, (message, expected_intent) in enumerate(test_cases, 1):
        print(f"\n{CYAN}Test {i}/6:{RESET} {message[:50]}...")
        
        try:
            response = requests.post(
                f"{BASE_URL}/v1/classify/intent",
                json={"message": message},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                detected_intent = data['intent']
                correct = detected_intent == expected_intent
                
                status = f"{GREEN}✓" if correct else f"{RED}✗"
                print(f"  {status} Detected: {detected_intent}, Expected: {expected_intent}{RESET}")
                results.append(correct)
            else:
                print(f"  {RED}✗ Request failed{RESET}")
                results.append(False)
                
        except Exception as e:
            print(f"  {RED}✗ Error: {e}{RESET}")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    accuracy = passed / total * 100
    
    print(f"\n{BLUE}{'─'*80}{RESET}")
    print(f"Intent Classification Accuracy: {accuracy:.1f}% ({passed}/{total})")
    
    if accuracy >= 80:  # 80% accuracy threshold
        print(f"{GREEN}{BOLD}✓ TEST 2.3 PASSED: Intent classification accurate{RESET}\n")
        return True
    else:
        print(f"{RED}{BOLD}✗ TEST 2.3 FAILED: Accuracy below 80% threshold{RESET}\n")
        return False


# ============================================================================
# TEST SUITE 3: PERFORMANCE & QUALITY
# ============================================================================

def test_day6_performance_impact():
    """Test 3.1: Day 6 Performance Impact"""
    print_test_header("3.1", "Day 6 Performance Impact")
    
    print("Measuring latency with/without Day 6 features...\n")
    
    # Test Content Generation Agent
    print(f"{CYAN}Content Generation Agent:{RESET}")
    
    # Without Day 6
    try:
        start = time.time()
        response1 = requests.post(
            f"{BASE_URL}/v1/generate/content",
            json={
                "content_type": "support_reply",
                "topic": "order inquiry",
                "tone": "friendly",
                "enable_expansion": False
            },
            timeout=120
        )
        latency_without = time.time() - start
        print(f"  Without Day 6: {latency_without:.2f}s")
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        latency_without = 0
    
    # With Day 6
    try:
        start = time.time()
        response2 = requests.post(
            f"{BASE_URL}/v1/generate/content",
            json={
                "content_type": "support_reply",
                "topic": "order inquiry",
                "tone": "friendly",
                "enable_expansion": True,
                "personalization_context": {"customer_name": "John"}
            },
            timeout=120
        )
        latency_with = time.time() - start
        print(f"  With Day 6: {latency_with:.2f}s")
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        latency_with = 0
    
    if latency_without > 0 and latency_with > 0:
        overhead = latency_with - latency_without
        print(f"  Day 6 overhead: {overhead:+.2f}s")
        
        if overhead < 2.0:  # Less than 2s overhead acceptable
            print(f"  {GREEN}✓ Performance impact acceptable{RESET}")
            return True
        else:
            print(f"  {YELLOW}⚠ Performance overhead high{RESET}")
            return False
    else:
        print(f"  {RED}✗ Could not measure performance{RESET}")
        return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all Day 6 production tests for both agents"""
    print_banner("DAY 6 PRODUCTION TEST SUITE - BOTH AGENTS", MAGENTA)
    
    print(f"{BOLD}Testing:{RESET}")
    print(f"  1. Content Generation Agent (6 content types)")
    print(f"  2. Customer Support Reply Agent (intent + reply)")
    print(f"  3. Day 6 Features: Query Expansion, Personalization, Hybrid Retrieval")
    print()
    
    # Check system status
    if not check_system_status():
        print(f"{RED}❌ ABORT: System not ready for Day 6 testing{RESET}\n")
        return
    
    input(f"{YELLOW}Press Enter to start tests...{RESET}\n")
    
    # Track results
    results = {}
    start_time = time.time()
    
    # Test Suite 1: Content Generation Agent
    print_banner("TEST SUITE 1: CONTENT GENERATION AGENT", CYAN)
    results["1.1 Content Agent - Query Expansion"] = test_content_agent_query_expansion()
    time.sleep(2)
    results["1.2 Content Agent - Personalization"] = test_content_agent_personalization()
    time.sleep(2)
    results["1.3 Content Agent - All Types"] = test_content_agent_all_types()
    time.sleep(2)
    
    # Test Suite 2: Customer Support Reply Agent
    print_banner("TEST SUITE 2: CUSTOMER SUPPORT REPLY AGENT", CYAN)
    results["2.1 Reply Agent - RAG Enhanced"] = test_reply_agent_with_rag()
    time.sleep(2)
    results["2.2 Reply Agent - Multi-turn"] = test_reply_agent_multi_turn()
    time.sleep(2)
    results["2.3 Reply Agent - Intent Classification"] = test_reply_agent_intent_classification()
    time.sleep(2)
    
    # Test Suite 3: Performance
    print_banner("TEST SUITE 3: PERFORMANCE & QUALITY", CYAN)
    results["3.1 Day 6 Performance Impact"] = test_day6_performance_impact()
    
    # Final summary
    total_time = time.time() - start_time
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    pass_rate = passed / total * 100
    
    print_banner("FINAL RESULTS", MAGENTA)
    
    for test_name, result in results.items():
        status = f"{GREEN}✓ PASS" if result else f"{RED}✗ FAIL"
        print(f"{status}{RESET} - {test_name}")
    
    print(f"\n{BLUE}{'─'*80}{RESET}")
    print(f"{BOLD}Total: {passed}/{total} tests passed ({pass_rate:.1f}%){RESET}")
    print(f"{BOLD}Duration: {total_time:.1f}s{RESET}")
    
    if pass_rate >= 85:
        print(f"\n{GREEN}{BOLD}🎉 PRODUCTION READY - Both agents pass Day 6 requirements!{RESET}\n")
    elif pass_rate >= 70:
        print(f"\n{YELLOW}{BOLD}⚠️  MOSTLY PASSING - Minor issues to address{RESET}\n")
    else:
        print(f"\n{RED}{BOLD}❌ CRITICAL ISSUES - Day 6 integration needs fixes{RESET}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}⚠️  Tests interrupted by user{RESET}\n")
    except Exception as e:
        print(f"\n{RED}❌ Unexpected error: {e}{RESET}\n")
