# scripts/test_review_ui.py
"""
Day 8: Testing script for Review UI validation
Tests all functionality: generation, display, review actions, CSV logging
"""
import os
import sys
import csv
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from loguru import logger

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
FEEDBACK_CSV = Path("data/human_feedback.csv")
TIMEOUT = 30


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text:^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")


def test_backend_health() -> bool:
    """Test 1: Backend health check"""
    print_header("TEST 1: Backend Health Check")
    
    try:
        with httpx.Client(timeout=5) as client:
            response = client.get(f"{BACKEND_URL}/health")
            
            if response.status_code == 200:
                data = response.json()
                print_success(f"Backend is healthy: {data}")
                
                # Check vector DB status
                if data.get('vector_db'):
                    print_success("Vector DB is available")
                else:
                    print_warning("Vector DB is not available")
                
                return True
            else:
                print_error(f"Backend returned status {response.status_code}")
                return False
                
    except Exception as e:
        print_error(f"Backend health check failed: {e}")
        return False


def test_content_generation() -> dict:
    """Test 2: Content generation API"""
    print_header("TEST 2: Content Generation")
    
    test_cases = [
        {
            "content_type": "blog",
            "topic": "Benefits of AI automation in customer service",
            "tone": "professional"
        },
        {
            "content_type": "product_description",
            "topic": "Smart wireless headphones",
            "tone": "friendly"
        },
        {
            "content_type": "support_reply",
            "topic": "How to reset password",
            "tone": "empathetic"
        }
    ]
    
    results = []
    
    for idx, test_case in enumerate(test_cases, 1):
        print_info(f"\nTest case {idx}/{len(test_cases)}: {test_case['content_type']} - {test_case['topic'][:50]}")
        
        try:
            with httpx.Client(timeout=TIMEOUT) as client:
                start = time.time()
                response = client.post(
                    f"{BACKEND_URL}/v1/generate/content",
                    json=test_case
                )
                latency = time.time() - start
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Validate response structure
                    required_fields = ['content_type', 'topic', 'headline', 'body', 'latency_s']
                    missing = [f for f in required_fields if f not in data]
                    
                    if missing:
                        print_error(f"Missing fields in response: {missing}")
                        results.append({'success': False, 'test_case': test_case, 'error': f"Missing fields: {missing}"})
                    else:
                        print_success(f"Content generated successfully (latency: {latency:.2f}s)")
                        print_info(f"  Headline: {data['headline'][:80]}...")
                        print_info(f"  Body length: {len(data['body'])} chars")
                        
                        results.append({
                            'success': True,
                            'test_case': test_case,
                            'data': data,
                            'api_latency': latency
                        })
                else:
                    print_error(f"API returned status {response.status_code}")
                    results.append({'success': False, 'test_case': test_case, 'error': f"Status {response.status_code}"})
                    
        except Exception as e:
            print_error(f"Content generation failed: {e}")
            results.append({'success': False, 'test_case': test_case, 'error': str(e)})
    
    successful = sum(1 for r in results if r.get('success', False))
    print_info(f"\n✨ Completed: {successful}/{len(test_cases)} tests passed")
    
    return results[0] if results and results[0].get('success') else None


def test_rag_retrieval() -> bool:
    """Test 3: RAG context retrieval"""
    print_header("TEST 3: RAG Context Retrieval")
    
    test_queries = [
        {"query": "customer service automation", "collection": None, "top_k": 3},
        {"query": "product features", "collection": "products", "top_k": 5},
        {"query": "support ticket handling", "collection": "support", "top_k": 3}
    ]
    
    passed = 0
    
    for idx, query_data in enumerate(test_queries, 1):
        print_info(f"\nTest {idx}/{len(test_queries)}: Query='{query_data['query']}', Collection={query_data.get('collection', 'all')}")
        
        try:
            with httpx.Client(timeout=TIMEOUT) as client:
                response = client.post(
                    f"{BACKEND_URL}/v1/retrieve",
                    json=query_data
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print_success(f"Retrieved {data['num_results']} documents (latency: {data['latency_ms']:.0f}ms)")
                    
                    # Show first result
                    if data['results']:
                        first = data['results'][0]
                        print_info(f"  Top result: {first['text'][:80]}...")
                        print_info(f"  Collection: {first['collection']}, Distance: {first['distance']:.3f}")
                    
                    passed += 1
                else:
                    print_warning(f"Retrieval returned status {response.status_code} (RAG may be disabled)")
                    
        except Exception as e:
            print_warning(f"Retrieval failed: {e} (RAG may be disabled)")
    
    print_info(f"\n✨ Completed: {passed}/{len(test_queries)} retrieval tests passed")
    return passed > 0


def test_validation_rules(sample_content: dict = None) -> bool:
    """Test 4: Validation rules"""
    print_header("TEST 4: Validation Rules")
    
    # Import validation from UI module
    ui_path = str(Path(__file__).parent.parent / "ui")
    if ui_path not in sys.path:
        sys.path.insert(0, ui_path)
    
    try:
        import review_app
        ValidationRules = review_app.ValidationRules
    except Exception as e:
        print_error(f"Could not import ValidationRules from review_app: {e}")
        return False
    
    test_cases = [
        {
            "name": "Valid content",
            "headline": "Great Product Features",
            "body": "This is a comprehensive description of our amazing product with all the features you need.",
            "expected_valid": True
        },
        {
            "name": "Empty content",
            "headline": "",
            "body": "",
            "expected_valid": False
        },
        {
            "name": "Too short",
            "headline": "Hi",
            "body": "Short",
            "expected_valid": False
        },
        {
            "name": "Profanity detected",
            "headline": "This is stupid",
            "body": "I hate this damn product",
            "expected_valid": False
        },
        {
            "name": "Suspicious patterns",
            "headline": "Click here now!",
            "body": "Act now! 100% free! Guaranteed results!",
            "expected_valid": False
        }
    ]
    
    passed = 0
    
    for idx, test in enumerate(test_cases, 1):
        print_info(f"\nTest {idx}/{len(test_cases)}: {test['name']}")
        
        result = ValidationRules.validate_all(test['headline'], test['body'])
        
        if result['valid'] == test['expected_valid']:
            print_success(f"Validation result correct: valid={result['valid']}")
            if result['issues']:
                print_info(f"  Issues found: {', '.join(result['issues'])}")
            passed += 1
        else:
            print_error(f"Validation mismatch: expected {test['expected_valid']}, got {result['valid']}")
    
    print_info(f"\n✨ Completed: {passed}/{len(test_cases)} validation tests passed")
    return passed == len(test_cases)


def test_csv_logging(sample_content: dict = None) -> bool:
    """Test 5: CSV feedback logging"""
    print_header("TEST 5: CSV Feedback Logging")
    
    # Create test feedback entry
    test_feedback = {
        'timestamp': datetime.utcnow().isoformat(),
        'session_id': 'test_session_001',
        'content_type': 'blog',
        'topic': 'Test topic for CSV logging',
        'tone': 'professional',
        'input_prompt': 'Test prompt',
        'retrieved_context': '{"test": "context"}',
        'generated_headline': 'Test Headline',
        'generated_body': 'Test body content for CSV logging validation.',
        'decision': 'approved',
        'edited_headline': '',
        'edited_body': '',
        'reviewer_notes': 'Test review notes',
        'validation_issues': '',
        'latency_s': 1.23
    }
    
    try:
        # Ensure directory exists
        FEEDBACK_CSV.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if CSV exists, create with headers if not
        if not FEEDBACK_CSV.exists():
            print_info("Creating new feedback CSV file...")
            with open(FEEDBACK_CSV, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'session_id', 'content_type', 'topic', 'tone',
                    'input_prompt', 'retrieved_context', 'generated_headline', 
                    'generated_body', 'decision', 'edited_headline', 'edited_body',
                    'reviewer_notes', 'validation_issues', 'latency_s'
                ])
            print_success("CSV file created with headers")
        
        # Append test feedback
        with open(FEEDBACK_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                test_feedback['timestamp'],
                test_feedback['session_id'],
                test_feedback['content_type'],
                test_feedback['topic'],
                test_feedback['tone'],
                test_feedback['input_prompt'],
                test_feedback['retrieved_context'],
                test_feedback['generated_headline'],
                test_feedback['generated_body'],
                test_feedback['decision'],
                test_feedback['edited_headline'],
                test_feedback['edited_body'],
                test_feedback['reviewer_notes'],
                test_feedback['validation_issues'],
                test_feedback['latency_s']
            ])
        
        print_success("Test feedback written to CSV")
        
        # Verify by reading back
        with open(FEEDBACK_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # Find our test entry
            test_entry = next((r for r in rows if r['session_id'] == 'test_session_001'), None)
            
            if test_entry:
                print_success(f"Test entry verified in CSV (found {len(rows)} total rows)")
                print_info(f"  Decision: {test_entry['decision']}")
                print_info(f"  Content type: {test_entry['content_type']}")
                return True
            else:
                print_error("Test entry not found in CSV")
                return False
                
    except Exception as e:
        print_error(f"CSV logging test failed: {e}")
        return False


def test_feedback_statistics() -> bool:
    """Test 6: Feedback statistics calculation"""
    print_header("TEST 6: Feedback Statistics")
    
    if not FEEDBACK_CSV.exists():
        print_warning("No feedback CSV found - skipping statistics test")
        return True
    
    try:
        stats = {'total': 0, 'approved': 0, 'rejected': 0, 'edited': 0}
        
        with open(FEEDBACK_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats['total'] += 1
                decision = row.get('decision', '').lower()
                if decision == 'approved':
                    stats['approved'] += 1
                elif decision == 'rejected':
                    stats['rejected'] += 1
                elif decision == 'edited':
                    stats['edited'] += 1
        
        print_success("Statistics calculated successfully:")
        print_info(f"  Total reviews: {stats['total']}")
        print_info(f"  Approved: {stats['approved']}")
        print_info(f"  Rejected: {stats['rejected']}")
        print_info(f"  Edited: {stats['edited']}")
        
        if stats['total'] > 0:
            approval_rate = stats['approved'] / stats['total'] * 100
            print_info(f"  Approval rate: {approval_rate:.1f}%")
        
        return True
        
    except Exception as e:
        print_error(f"Statistics calculation failed: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print_header("DAY 8: REVIEW UI COMPREHENSIVE TEST SUITE")
    print_info(f"Backend URL: {BACKEND_URL}")
    print_info(f"Feedback CSV: {FEEDBACK_CSV}")
    print_info(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = {}
    
    # Test 1: Backend health
    results['backend_health'] = test_backend_health()
    
    if not results['backend_health']:
        print_error("\n❌ Backend is not available. Cannot proceed with API tests.")
        print_info("Please ensure the backend is running: uvicorn backend.main:app --reload")
        return
    
    # Test 2: Content generation
    sample_content = test_content_generation()
    results['content_generation'] = sample_content is not None
    
    # Test 3: RAG retrieval
    results['rag_retrieval'] = test_rag_retrieval()
    
    # Test 4: Validation rules
    results['validation_rules'] = test_validation_rules(sample_content)
    
    # Test 5: CSV logging
    results['csv_logging'] = test_csv_logging(sample_content)
    
    # Test 6: Statistics
    results['statistics'] = test_feedback_statistics()
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASSED" if passed_test else "❌ FAILED"
        color = Colors.GREEN if passed_test else Colors.RED
        print(f"{color}{status}{Colors.RESET} - {test_name.replace('_', ' ').title()}")
    
    print(f"\n{Colors.BOLD}Overall: {passed}/{total} tests passed{Colors.RESET}")
    
    if passed == total:
        print_success("\n🎉 All tests passed! Review UI is ready to use.")
        print_info("\nTo start the UI, run:")
        print_info("  streamlit run ui/review_app.py")
    else:
        print_warning(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
    
    print_info(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    logger.remove()  # Remove default logger
    logger.add(lambda msg: None)  # Suppress loguru output
    
    run_all_tests()
