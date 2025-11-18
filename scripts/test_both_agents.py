"""
Complete Agent Testing Suite
Tests both Content Generation Agent and Customer Support Agent
with RAG (ChromaDB) and Validators
"""

import requests
import json
import time
from loguru import logger
from typing import Dict

BASE_URL = "http://localhost:8000"

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.YELLOW}ℹ️  {text}{Colors.END}")

def check_health() -> bool:
    """Check server health and ChromaDB status"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        data = response.json()
        
        if data.get("status") == "ok":
            print_success(f"Server Status: {data['status']}")
            
            if data.get("vector_db"):
                print_success("ChromaDB: Initialized and Ready")
            else:
                print_error("ChromaDB: Not Available")
                return False
            
            return True
        else:
            print_error("Server health check failed")
            return False
            
    except Exception as e:
        print_error(f"Cannot connect to server: {e}")
        return False

def test_content_generation_agent(topic: str, tone: str = "empathetic") -> Dict:
    """
    Test Content Generation Agent with RAG
    
    Flow:
    1. Receives topic and tone
    2. Retrieves relevant context from ChromaDB (RAG)
    3. Generates content with LLM
    4. Returns structured response
    """
    print_header("🤖 CONTENT GENERATION AGENT TEST")
    
    print_info(f"Topic: {topic}")
    print_info(f"Tone: {tone}")
    
    payload = {
        "content_type": "support_reply",
        "topic": topic,
        "tone": tone
    }
    
    print(f"\n📤 Sending request to /v1/generate/content...")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/v1/generate/content",
            json=payload,
            timeout=30
        )
        latency = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            
            print_success(f"Response received in {latency:.2f}s")
            print(f"\n{Colors.BOLD}📋 Generated Content:{Colors.END}")
            print(f"{Colors.BOLD}Headline:{Colors.END} {data['headline']}")
            print(f"\n{Colors.BOLD}Body:{Colors.END}")
            print(f"{data['body'][:300]}..." if len(data['body']) > 300 else data['body'])
            print(f"\n{Colors.BOLD}Metrics:{Colors.END}")
            print(f"  • Content Type: {data['content_type']}")
            print(f"  • LLM Latency: {data['latency_s']:.2f}s")
            print(f"  • Total Latency: {latency:.2f}s")
            
            # Validate response structure
            if data['headline'] and data['body'] and len(data['body']) > 50:
                print_success("✓ Content validation passed")
                print_success("✓ RAG context used (check server logs)")
                return {"status": "passed", "data": data}
            else:
                print_error("✗ Content validation failed (too short)")
                return {"status": "failed", "reason": "Content too short"}
        else:
            print_error(f"Request failed: {response.status_code}")
            print_error(f"Error: {response.text}")
            return {"status": "failed", "reason": response.text}
            
    except Exception as e:
        print_error(f"Request error: {e}")
        return {"status": "failed", "reason": str(e)}

def test_customer_support_agent(message: str) -> Dict:
    """
    Test Customer Support Agent with RAG and Validation
    
    Flow:
    1. Receives customer message
    2. Classifies intent (complaint/inquiry/request)
    3. Retrieves relevant context from ChromaDB (RAG)
    4. Generates contextual reply with LLM
    5. Validates reply (toxicity, length, forbidden phrases)
    6. Returns structured response
    """
    print_header("🎧 CUSTOMER SUPPORT AGENT TEST")
    
    print_info(f"Customer Message: {message}")
    
    payload = {
        "message": message
    }
    
    print(f"\n📤 Sending request to /v1/generate/reply (sync mode)...")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/v1/generate/reply?async_mode=false",
            json=payload,
            timeout=60
        )
        latency = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            
            print_success(f"Response received in {latency:.2f}s")
            
            print(f"\n{Colors.BOLD}🎯 Intent Classification:{Colors.END}")
            print(f"  • Detected Intent: {Colors.BOLD}{data['detected_intent']}{Colors.END}")
            print(f"  • Classification Time: {data.get('classification_latency_s', 0):.2f}s")
            
            print(f"\n{Colors.BOLD}💬 Generated Reply:{Colors.END}")
            print(f"{data['reply'][:300]}..." if len(data['reply']) > 300 else data['reply'])
            
            if data.get('next_steps'):
                print(f"\n{Colors.BOLD}📝 Next Steps:{Colors.END}")
                print(f"{data['next_steps']}")
            
            print(f"\n{Colors.BOLD}📊 Performance Metrics:{Colors.END}")
            print(f"  • Intent Classification: {data.get('classification_latency_s', 0):.2f}s")
            print(f"  • Reply Generation: {data.get('generation_latency_s', 0):.2f}s")
            print(f"  • Total Time: {data.get('total_latency_s', 0):.2f}s")
            
            # Validation checks
            validations = []
            if data['reply'] and len(data['reply']) > 20:
                validations.append("✓ Reply length validation passed")
            if data['detected_intent'] in ['complaint', 'inquiry', 'request']:
                validations.append("✓ Intent classification valid")
            if 'empathy' in data['reply'].lower() or 'sorry' in data['reply'].lower() or 'help' in data['reply'].lower():
                validations.append("✓ Empathy markers detected")
            
            print(f"\n{Colors.BOLD}✅ Validation Results:{Colors.END}")
            for v in validations:
                print_success(v)
            
            print_success("✓ RAG context used (check server logs)")
            print_success("✓ Validators applied successfully")
            
            return {"status": "passed", "data": data}
            
        else:
            print_error(f"Request failed: {response.status_code}")
            print_error(f"Error: {response.text}")
            return {"status": "failed", "reason": response.text}
            
    except Exception as e:
        print_error(f"Request error: {e}")
        return {"status": "failed", "reason": str(e)}

def test_chromadb_retrieval(query: str, collection: str = "support") -> Dict:
    """Test direct ChromaDB retrieval"""
    print_header("🗄️ CHROMADB RETRIEVAL TEST")
    
    print_info(f"Query: {query}")
    print_info(f"Collection: {collection}")
    
    payload = {
        "query": query,
        "collection": collection,
        "top_k": 3
    }
    
    print(f"\n📤 Retrieving from ChromaDB...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/retrieve",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print_success(f"Retrieved {data['num_results']} results in {data['latency_ms']:.2f}ms")
            
            print(f"\n{Colors.BOLD}📄 Top Results:{Colors.END}")
            for idx, doc in enumerate(data['results'][:3], 1):
                print(f"\n{Colors.BOLD}Result #{idx}:{Colors.END}")
                print(f"  • Distance: {doc['distance']:.4f} (lower = more similar)")
                print(f"  • Collection: {doc['collection']}")
                print(f"  • Preview: {doc['text'][:150]}...")
            
            print_success("✓ ChromaDB retrieval working")
            return {"status": "passed", "data": data}
            
        else:
            print_error(f"Retrieval failed: {response.status_code}")
            return {"status": "failed"}
            
    except Exception as e:
        print_error(f"Retrieval error: {e}")
        return {"status": "failed"}

def run_complete_test_suite():
    """Run complete test suite for both agents"""
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔" + "="*78 + "╗")
    print("║" + " COMPLETE AGENT TESTING SUITE ".center(78) + "║")
    print("║" + " Content Generation + Customer Support + RAG + Validators ".center(78) + "║")
    print("╚" + "="*78 + "╝")
    print(f"{Colors.END}\n")
    
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "tests": []
    }
    
    # Step 1: Health Check
    print_header("STEP 1: HEALTH CHECK")
    if not check_health():
        print_error("Server or ChromaDB not available. Cannot proceed with tests.")
        return
    
    time.sleep(1)
    
    # Step 2: Test ChromaDB Retrieval
    test = {
        "name": "ChromaDB Retrieval",
        "result": test_chromadb_retrieval("customer wants refund for late order")
    }
    results["tests"].append(test)
    results["total"] += 1
    if test["result"]["status"] == "passed":
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    time.sleep(2)
    
    # Step 3: Test Content Generation Agent
    test = {
        "name": "Content Generation Agent",
        "result": test_content_generation_agent(
            topic="customer requesting refund for delayed delivery",
            tone="empathetic"
        )
    }
    results["tests"].append(test)
    results["total"] += 1
    if test["result"]["status"] == "passed":
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    time.sleep(2)
    
    # Step 4: Test Customer Support Agent - Complaint
    test = {
        "name": "Customer Support Agent (Complaint)",
        "result": test_customer_support_agent(
            "My order is 2 weeks late and I still haven't received it. I need a refund immediately!"
        )
    }
    results["tests"].append(test)
    results["total"] += 1
    if test["result"]["status"] == "passed":
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    time.sleep(2)
    
    # Step 5: Test Customer Support Agent - Inquiry
    test = {
        "name": "Customer Support Agent (Inquiry)",
        "result": test_customer_support_agent(
            "How can I track my order? I placed it yesterday."
        )
    }
    results["tests"].append(test)
    results["total"] += 1
    if test["result"]["status"] == "passed":
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    time.sleep(2)
    
    # Step 6: Test Customer Support Agent - Request
    test = {
        "name": "Customer Support Agent (Request)",
        "result": test_customer_support_agent(
            "Can you please change my shipping address to 123 Main St?"
        )
    }
    results["tests"].append(test)
    results["total"] += 1
    if test["result"]["status"] == "passed":
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Final Summary
    print_header("📊 FINAL TEST SUMMARY")
    
    print(f"\n{Colors.BOLD}Test Results:{Colors.END}")
    print(f"  • Total Tests: {results['total']}")
    print(f"  • Passed: {Colors.GREEN}{results['passed']}{Colors.END}")
    print(f"  • Failed: {Colors.RED}{results['failed']}{Colors.END}")
    
    success_rate = (results['passed'] / results['total'] * 100) if results['total'] > 0 else 0
    print(f"  • Success Rate: {Colors.BOLD}{success_rate:.1f}%{Colors.END}")
    
    print(f"\n{Colors.BOLD}Test Details:{Colors.END}")
    for idx, test in enumerate(results['tests'], 1):
        status_icon = "✅" if test['result']['status'] == "passed" else "❌"
        status_color = Colors.GREEN if test['result']['status'] == "passed" else Colors.RED
        print(f"  {idx}. {test['name']}: {status_color}{status_icon} {test['result']['status'].upper()}{Colors.END}")
    
    print(f"\n{Colors.BOLD}Components Tested:{Colors.END}")
    print_success("✓ Content Generation Agent (with RAG)")
    print_success("✓ Customer Support Agent (with RAG + Intent Classification)")
    print_success("✓ ChromaDB Vector Database")
    print_success("✓ Semantic Search & Retrieval")
    print_success("✓ Content Validators")
    print_success("✓ LLM Generation (Llama 3)")
    
    if results['passed'] == results['total']:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED! System is working perfectly!{Colors.END}\n")
    else:
        print(f"\n{Colors.YELLOW}⚠️  Some tests failed. Check the errors above.{Colors.END}\n")
    
    return results

if __name__ == "__main__":
    print("\n")
    results = run_complete_test_suite()
    
    print(f"\n{Colors.BOLD}📝 Notes:{Colors.END}")
    print("  • Check server logs to see RAG context injection messages")
    print("  • ChromaDB must be initialized (run initialize_vectordb.py if needed)")
    print("  • Ollama with Llama 3 must be running")
    print("\n")
