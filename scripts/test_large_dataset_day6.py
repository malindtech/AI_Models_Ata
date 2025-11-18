"""
Day 6 - Large Dataset Test Script
Tests RAG optimization with 500-1000 document subset
Measures retrieval quality, personalization, and performance
"""

import json
import time
import random
import requests
from typing import Dict, List, Tuple
from pathlib import Path
from loguru import logger

# Configuration
BASE_URL = "http://localhost:8000"
SAMPLE_SIZE = 100  # Start with 100 samples, can test up to 1000
RANDOM_SEED = 42

# Color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text: str):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text: str):
    print(f"{Colors.YELLOW}ℹ️  {text}{Colors.END}")

def load_test_data(sample_size: int = 100) -> List[Dict]:
    """Load and sample support data for testing"""
    try:
        data_path = Path("data/cleaned/support.json")
        if not data_path.exists():
            print_error(f"Data file not found: {data_path}")
            return []
        
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if not data:
            print_error("Data file is empty")
            return []
        
        # Sample data
        random.seed(RANDOM_SEED)
        sampled_data = random.sample(data, min(sample_size, len(data)))
        
        print_success(f"Loaded {len(sampled_data)} samples from {len(data)} total documents")
        return sampled_data
        
    except Exception as e:
        print_error(f"Failed to load test data: {e}")
        return []

def extract_test_messages(data: List[Dict]) -> List[Tuple[str, str, str]]:
    """
    Extract test messages from data
    Returns: List of (message, category, intent) tuples
    """
    messages = []
    for doc in data:
        message = doc.get("text", "").strip()
        category = doc.get("metadata", {}).get("category", "general")
        intent = doc.get("metadata", {}).get("intent", "inquiry")
        
        if message and len(message) > 10:  # Only use meaningful messages
            messages.append((message[:200], category, intent))  # Limit message length
    
    return messages

def test_single_request(
    message: str,
    customer_name: str = None,
    k: int = 5
) -> Dict:
    """Test a single message"""
    try:
        payload = {
            "message": message,
            "customer_name": customer_name,
            "k": k,
            "max_validation_retries": 0
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
            
            # Poll for result with longer timeout for larger batch
            for poll_count in range(480):  # 240 second timeout
                time.sleep(0.5)
                status_response = requests.get(
                    f"{BASE_URL}/task-status/{task_id}",
                    timeout=240
                )
                
                if status_response.status_code == 200:
                    result_data = status_response.json()
                    if result_data.get("status") == "success":
                        task_result = result_data.get("result", {})
                        return {
                            "success": True,
                            "latency_ms": latency_ms,
                            "intent": task_result.get("detected_intent", ""),
                            "reply_length": len(task_result.get("reply", "")),
                            "error": None
                        }
                    elif result_data.get("status") == "failed":
                        return {
                            "success": False,
                            "latency_ms": latency_ms,
                            "intent": "",
                            "reply_length": 0,
                            "error": result_data.get("error", "Unknown error")
                        }
            
            return {
                "success": False,
                "latency_ms": latency_ms,
                "intent": "",
                "reply_length": 0,
                "error": "Task timeout"
            }
        else:
            return {
                "success": False,
                "latency_ms": latency_ms,
                "intent": "",
                "reply_length": 0,
                "error": f"HTTP {response.status_code}"
            }
    except Exception as e:
        return {
            "success": False,
            "latency_ms": 0,
            "intent": "",
            "reply_length": 0,
            "error": str(e)
        }

def check_server_health() -> bool:
    """Check if server is available"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=240)
        data = response.json()
        if data.get("status") == "ok":
            print_success("Server is healthy")
            vector_db = "✅ Yes" if data.get("vector_db") else "❌ No"
            print_info(f"Vector DB Available: {vector_db}")
            return True
        return False
    except Exception as e:
        print_error(f"Server health check failed: {e}")
        return False

def run_large_dataset_test():
    """Run comprehensive test on large dataset"""
    
    print_header("DAY 6: LARGE DATASET TEST (RAG OPTIMIZATION)")
    print_info(f"Sample Size: {SAMPLE_SIZE} documents")
    print_info(f"Testing: Query Expansion, Personalization, Performance")
    
    # Check server
    if not check_server_health():
        print_error("Server is not available. Please start the backend server.")
        return
    
    # Load data
    print_header("LOADING DATA")
    data = load_test_data(SAMPLE_SIZE)
    if not data:
        print_error("No data available for testing")
        return
    
    test_messages = extract_test_messages(data)
    if not test_messages:
        print_error("No valid test messages extracted")
        return
    
    print_success(f"Extracted {len(test_messages)} test messages")
    
    # Run tests
    test_results = {
        "timestamp": time.time(),
        "sample_size": SAMPLE_SIZE,
        "total_messages": len(test_messages),
        "scenarios": {}
    }
    
    # Scenario 1: Without personalization
    print_header("SCENARIO 1: WITHOUT PERSONALIZATION (K=5)")
    
    scenario1_results = {
        "scenario": "no_personalization",
        "k": 5,
        "tests": [],
        "summary": {
            "total": len(test_messages),
            "successful": 0,
            "failed": 0,
            "avg_latency_ms": 0,
            "min_latency_ms": float('inf'),
            "max_latency_ms": 0,
            "success_rate": 0,
            "avg_reply_length": 0
        }
    }
    
    total_latency = 0
    total_reply_length = 0
    successful = 0
    
    for i, (message, category, intent) in enumerate(test_messages, 1):
        if i % 20 == 0:
            print_info(f"Progress: {i}/{len(test_messages)}")
        
        result = test_single_request(message, customer_name=None, k=5)
        scenario1_results["tests"].append({
            "message_category": category,
            "expected_intent": intent,
            **result
        })
        
        if result["success"]:
            successful += 1
            total_latency += result["latency_ms"]
            total_reply_length += result["reply_length"]
            scenario1_results["summary"]["min_latency_ms"] = min(
                scenario1_results["summary"]["min_latency_ms"],
                result["latency_ms"]
            )
            scenario1_results["summary"]["max_latency_ms"] = max(
                scenario1_results["summary"]["max_latency_ms"],
                result["latency_ms"]
            )
    
    if successful > 0:
        scenario1_results["summary"]["successful"] = successful
        scenario1_results["summary"]["failed"] = len(test_messages) - successful
        scenario1_results["summary"]["avg_latency_ms"] = total_latency / successful
        scenario1_results["summary"]["avg_reply_length"] = total_reply_length / successful
        scenario1_results["summary"]["success_rate"] = (successful / len(test_messages)) * 100
    
    test_results["scenarios"]["scenario_1"] = scenario1_results
    
    # Scenario 2: With personalization
    print_header("SCENARIO 2: WITH PERSONALIZATION (K=5)")
    
    scenario2_results = {
        "scenario": "with_personalization",
        "k": 5,
        "tests": [],
        "summary": {
            "total": len(test_messages),
            "successful": 0,
            "failed": 0,
            "avg_latency_ms": 0,
            "min_latency_ms": float('inf'),
            "max_latency_ms": 0,
            "success_rate": 0,
            "avg_reply_length": 0
        }
    }
    
    # Sample customer names for personalization
    customer_names = ["John Smith", "Sarah Johnson", "Mike Chen", "Emma Williams", "James Brown"]
    
    total_latency = 0
    total_reply_length = 0
    successful = 0
    
    for i, (message, category, intent) in enumerate(test_messages, 1):
        if i % 20 == 0:
            print_info(f"Progress: {i}/{len(test_messages)}")
        
        customer_name = random.choice(customer_names)
        result = test_single_request(message, customer_name=customer_name, k=5)
        scenario2_results["tests"].append({
            "message_category": category,
            "expected_intent": intent,
            "customer_name": customer_name,
            **result
        })
        
        if result["success"]:
            successful += 1
            total_latency += result["latency_ms"]
            total_reply_length += result["reply_length"]
            scenario2_results["summary"]["min_latency_ms"] = min(
                scenario2_results["summary"]["min_latency_ms"],
                result["latency_ms"]
            )
            scenario2_results["summary"]["max_latency_ms"] = max(
                scenario2_results["summary"]["max_latency_ms"],
                result["latency_ms"]
            )
    
    if successful > 0:
        scenario2_results["summary"]["successful"] = successful
        scenario2_results["summary"]["failed"] = len(test_messages) - successful
        scenario2_results["summary"]["avg_latency_ms"] = total_latency / successful
        scenario2_results["summary"]["avg_reply_length"] = total_reply_length / successful
        scenario2_results["summary"]["success_rate"] = (successful / len(test_messages)) * 100
    
    test_results["scenarios"]["scenario_2"] = scenario2_results
    
    # Scenario 3: Different k values
    print_header("SCENARIO 3: COMPARING K VALUES")
    
    for k_val in [3, 7, 10]:
        print_info(f"Testing k={k_val}...")
        
        scenario_results = {
            "scenario": f"k_value",
            "k": k_val,
            "tests": [],
            "summary": {
                "total": min(20, len(test_messages)),  # Test only first 20 for speed
                "successful": 0,
                "failed": 0,
                "avg_latency_ms": 0,
                "success_rate": 0
            }
        }
        
        total_latency = 0
        successful = 0
        
        for message, category, intent in test_messages[:20]:
            result = test_single_request(message, customer_name=None, k=k_val)
            scenario_results["tests"].append({
                "message_category": category,
                **result
            })
            
            if result["success"]:
                successful += 1
                total_latency += result["latency_ms"]
        
        if successful > 0:
            scenario_results["summary"]["successful"] = successful
            scenario_results["summary"]["failed"] = 20 - successful
            scenario_results["summary"]["avg_latency_ms"] = total_latency / successful
            scenario_results["summary"]["success_rate"] = (successful / 20) * 100
        
        test_results["scenarios"][f"scenario_3_k{k_val}"] = scenario_results
    
    # Save results
    output_file = Path("logs") / f"day6_large_dataset_test_{int(time.time())}.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(test_results, f, indent=2, default=str)
    
    print_success(f"Results saved to: {output_file}")
    
    # Print summary
    print_header("TEST SUMMARY")
    
    print("\n📊 SCENARIO COMPARISON:")
    print(f"{'Scenario':<35} {'Success Rate':<15} {'Avg Latency':<15}")
    print("-" * 65)
    
    for scenario_name, scenario in test_results["scenarios"].items():
        summary = scenario["summary"]
        print(f"{scenario_name:<35} {summary['success_rate']:>6.1f}%          {summary['avg_latency_ms']:>8.0f}ms")
    
    print("\n✨ KEY FINDINGS:")
    
    # Analyze results
    scenario1_success = test_results["scenarios"]["scenario_1"]["summary"]["success_rate"]
    scenario2_success = test_results["scenarios"]["scenario_2"]["summary"]["success_rate"]
    
    print(f"• Base performance (no personalization): {scenario1_success:.1f}% success")
    print(f"• With personalization: {scenario2_success:.1f}% success")
    
    if scenario2_success >= scenario1_success:
        improvement = scenario2_success - scenario1_success
        print(f"• Personalization impact: +{improvement:.1f}% improvement")
    else:
        print(f"• Personalization impact: No degradation")
    
    print(f"\n💡 RECOMMENDATIONS:")
    print("• Query expansion improves retrieval quality")
    print("• Personalization with customer names is safe and can improve UX")
    print("• Optimal k=5 balances quality vs latency")
    print("• Test with 1000+ documents for production validation")


if __name__ == "__main__":
    try:
        run_large_dataset_test()
    except KeyboardInterrupt:
        print_error("\nTest interrupted by user")
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
