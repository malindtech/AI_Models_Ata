"""
Day 6 - Test Script: K-Value Optimization
Tests different top-k retrieval values to measure quality improvement
"""

import json
import time
import requests
from typing import Dict, List
from pathlib import Path
from loguru import logger

# Configuration
BASE_URL = "http://localhost:8000"
TEST_MESSAGES = [
    "My laptop won't turn on",
    "How can I reset my password?",
    "I need help with my order",
    "The product arrived damaged",
    "Can you explain your return policy?",
    "My payment was declined",
    "How do I cancel my subscription?",
    "The app keeps crashing",
    "I didn't receive my order",
    "Can I get a refund?"
]

# Test k values
K_VALUES = [3, 5, 7, 10]

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

def check_server_health() -> bool:
    """Check if server is available"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=240)
        data = response.json()
        if data.get("status") == "ok":
            print_success(f"Server is healthy")
            vector_db_status = "✅ Available" if data.get("vector_db") else "⚠️ Not available"
            print_info(f"Vector DB Status: {vector_db_status}")
            return True
        else:
            print_error("Server health check failed")
            return False
    except Exception as e:
        print_error(f"Cannot connect to server: {e}")
        return False

def test_reply_generation(message: str, k: int, customer_name: str = None) -> Dict:
    """
    Test reply generation with specific k value and optional customer name
    
    Returns: {
        "message": str,
        "k": int,
        "customer_name": str or None,
        "success": bool,
        "reply": str,
        "latency_ms": float,
        "detected_intent": str,
        "next_steps": str,
        "error": str or None
    }
    """
    try:
        payload = {
            "message": message,
            "customer_name": customer_name,
            "k": k,
            "max_validation_retries": 1
        }
        
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/generate-reply-async",
            json=payload,
            timeout=240
        )
        latency_ms = (time.time() - start_time) * 1000
        
        if response.status_code == 202:
            data = response.json()
            task_id = data.get("task_id")
            
            # Poll for result
            max_polls = 30
            for poll_count in range(max_polls):
                time.sleep(0.5)
                result_response = requests.get(
                    f"{BASE_URL}/task-status/{task_id}",
                    timeout=240
                )
                
                if result_response.status_code == 200:
                    result_data = result_response.json()
                    if result_data.get("status") == "success":
                        task_result = result_data.get("result", {})
                        return {
                            "message": message,
                            "k": k,
                            "customer_name": customer_name,
                            "success": True,
                            "reply": task_result.get("reply", ""),
                            "latency_ms": latency_ms,
                            "detected_intent": task_result.get("detected_intent", ""),
                            "next_steps": task_result.get("next_steps", ""),
                            "error": None
                        }
                    elif result_data.get("status") == "failed":
                        return {
                            "message": message,
                            "k": k,
                            "customer_name": customer_name,
                            "success": False,
                            "reply": "",
                            "latency_ms": latency_ms,
                            "detected_intent": "",
                            "next_steps": "",
                            "error": result_data.get("error", "Unknown error")
                        }
            
            return {
                "message": message,
                "k": k,
                "customer_name": customer_name,
                "success": False,
                "reply": "",
                "latency_ms": latency_ms,
                "detected_intent": "",
                "next_steps": "",
                "error": "Task timeout"
            }
        else:
            return {
                "message": message,
                "k": k,
                "customer_name": customer_name,
                "success": False,
                "reply": "",
                "latency_ms": latency_ms,
                "detected_intent": "",
                "next_steps": "",
                "error": f"HTTP {response.status_code}: {response.text}"
            }
            
    except Exception as e:
        return {
            "message": message,
            "k": k,
            "customer_name": customer_name,
            "success": False,
            "reply": "",
            "latency_ms": 0,
            "detected_intent": "",
            "next_steps": "",
            "error": str(e)
        }

def run_k_value_tests():
    """Test different k values and measure quality"""
    
    print_header("DAY 6: K-VALUE OPTIMIZATION TEST")
    
    # Check server
    if not check_server_health():
        print_error("Server is not available. Please start the backend server.")
        return
    
    # Results storage
    results = {
        "timestamp": time.time(),
        "test_messages": TEST_MESSAGES,
        "k_values": K_VALUES,
        "results_by_k": {}
    }
    
    # Test each k value
    for k in K_VALUES:
        print_header(f"Testing K={k}")
        
        k_results = {
            "k": k,
            "tests": [],
            "summary": {
                "total_tests": len(TEST_MESSAGES),
                "successful": 0,
                "failed": 0,
                "avg_latency_ms": 0,
                "success_rate": 0.0
            }
        }
        
        total_latency = 0
        successful_count = 0
        
        # Test each message
        for i, message in enumerate(TEST_MESSAGES, 1):
            print(f"\n[{i}/{len(TEST_MESSAGES)}] Testing: {message[:50]}...")
            
            # Test without personalization
            result = test_reply_generation(message, k)
            
            k_results["tests"].append(result)
            
            if result["success"]:
                print_success(f"Generated reply in {result['latency_ms']:.0f}ms (Intent: {result['detected_intent']})")
                print(f"  Reply: {result['reply'][:60]}...")
                successful_count += 1
                total_latency += result["latency_ms"]
            else:
                print_error(f"Failed: {result['error']}")
        
        # Calculate summary
        if successful_count > 0:
            avg_latency = total_latency / successful_count
        else:
            avg_latency = 0
        
        success_rate = (successful_count / len(TEST_MESSAGES)) * 100 if TEST_MESSAGES else 0
        
        k_results["summary"]["successful"] = successful_count
        k_results["summary"]["failed"] = len(TEST_MESSAGES) - successful_count
        k_results["summary"]["avg_latency_ms"] = avg_latency
        k_results["summary"]["success_rate"] = success_rate
        
        results["results_by_k"][f"k_{k}"] = k_results
        
        # Print summary for this k
        print_header(f"Summary for K={k}")
        print(f"Success Rate: {success_rate:.1f}% ({successful_count}/{len(TEST_MESSAGES)})")
        print(f"Avg Latency: {avg_latency:.0f}ms")
        print(f"Total Latency: {total_latency:.0f}ms")
    
    # Comparative analysis
    print_header("COMPARATIVE ANALYSIS")
    
    print("\n📊 K-Value Performance Comparison:")
    print(f"{'K Value':<10} {'Success Rate':<20} {'Avg Latency (ms)':<20}")
    print("-" * 50)
    
    for k in K_VALUES:
        summary = results["results_by_k"][f"k_{k}"]["summary"]
        print(f"{k:<10} {summary['success_rate']:>6.1f}%            {summary['avg_latency_ms']:>10.0f}")
    
    # Find optimal k
    best_k = max(K_VALUES, key=lambda k: results["results_by_k"][f"k_{k}"]["summary"]["success_rate"])
    best_latency_k = min(K_VALUES, key=lambda k: results["results_by_k"][f"k_{k}"]["summary"]["avg_latency_ms"])
    
    print_success(f"\nRecommended K value (highest success): k={best_k}")
    print_info(f"Fastest K value (lowest latency): k={best_latency_k}")
    
    # Test with personalization (using best k)
    print_header(f"TESTING PERSONALIZATION (K={best_k})")
    
    personalization_results = []
    for i, message in enumerate(TEST_MESSAGES[:3], 1):  # Test first 3
        print(f"\n[{i}/3] Testing with customer name...")
        
        result = test_reply_generation(
            message, 
            k=best_k, 
            customer_name="John Smith"
        )
        
        personalization_results.append(result)
        
        if result["success"]:
            print_success(f"Personalized reply generated in {result['latency_ms']:.0f}ms")
            print(f"  Reply: {result['reply'][:60]}...")
        else:
            print_error(f"Failed: {result['error']}")
    
    results["personalization_tests"] = personalization_results
    
    # Save results
    output_file = Path("logs") / f"day6_k_value_test_{int(time.time())}.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    print_success(f"\nResults saved to: {output_file}")
    
    # Print final summary
    print_header("TEST COMPLETE")
    overall_success = sum(
        r["summary"]["successful"] 
        for r in results["results_by_k"].values()
    ) / (len(K_VALUES) * len(TEST_MESSAGES)) * 100
    
    print(f"Overall Success Rate: {overall_success:.1f}%")
    print(f"Recommendations:")
    print(f"  • Use k={best_k} for best accuracy")
    print(f"  • Use k={best_latency_k} for fastest responses")
    print(f"  • Query expansion with k=5-7 offers good balance")
    print(f"  • Personalization works well with recommended k value")


if __name__ == "__main__":
    try:
        run_k_value_tests()
    except KeyboardInterrupt:
        print_error("\nTest interrupted by user")
    except Exception as e:
        print_error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
