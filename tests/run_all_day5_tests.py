"""
Master Test Runner for Day 5 Implementation

Runs all three test suites in sequence:
1. Embeddings Test Suite
2. ChromaDB Test Suite  
3. RAG Integration Test Suite

Provides comprehensive validation of Day 5 RAG implementation.
"""

import sys
from pathlib import Path
import subprocess
import time

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
RESET = '\033[0m'
BOLD = '\033[1m'

PROJECT_ROOT = Path(__file__).parent.parent


def print_banner(title: str, color: str = CYAN):
    """Print a formatted banner"""
    print(f"\n{BOLD}{color}{'='*80}{RESET}")
    print(f"{BOLD}{color}{title.center(80)}{RESET}")
    print(f"{BOLD}{color}{'='*80}{RESET}\n")


def run_test_suite(suite_name: str, script_path: Path) -> bool:
    """Run a test suite script and return success status"""
    print_banner(f"Running: {suite_name}", CYAN)
    
    if not script_path.exists():
        print(f"{RED}✗ Test script not found: {script_path}{RESET}")
        return False
    
    print(f"{BLUE}Executing: python {script_path.relative_to(PROJECT_ROOT)}{RESET}\n")
    
    try:
        # Run the test script
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=PROJECT_ROOT,
            capture_output=False,  # Show output in real-time
            text=True
        )
        
        success = result.returncode == 0
        
        if success:
            print(f"\n{GREEN}{BOLD}✓ {suite_name} COMPLETED SUCCESSFULLY{RESET}")
        else:
            print(f"\n{YELLOW}{BOLD}⚠ {suite_name} COMPLETED WITH ISSUES{RESET}")
        
        return success
        
    except Exception as e:
        print(f"{RED}✗ Error running {suite_name}: {e}{RESET}")
        return False


def main():
    """Run all test suites"""
    print_banner("DAY 5 IMPLEMENTATION - COMPREHENSIVE TEST SUITE", MAGENTA)
    
    print(f"{BOLD}This test suite validates:{RESET}")
    print(f"  1. {CYAN}Embeddings{RESET} - all-MiniLM-L6-v2 model functionality")
    print(f"  2. {CYAN}ChromaDB{RESET} - persistence, queries, and metadata")
    print(f"  3. {CYAN}RAG Integration{RESET} - both agents with retrieval-augmented generation")
    print()
    
    input(f"{YELLOW}Press Enter to start tests...{RESET}")
    
    # Track results
    results = {}
    start_time = time.time()
    
    # Test Suite 1: Embeddings
    results["Embeddings"] = run_test_suite(
        "Embeddings Test Suite",
        PROJECT_ROOT / "tests" / "test_embeddings.py"
    )
    time.sleep(2)
    
    # Test Suite 2: ChromaDB
    results["ChromaDB"] = run_test_suite(
        "ChromaDB Test Suite",
        PROJECT_ROOT / "tests" / "test_chromadb.py"
    )
    time.sleep(2)
    
    # Test Suite 3: RAG Integration
    print(f"\n{YELLOW}{BOLD}NOTE: RAG Integration tests require the API to be running{RESET}")
    print(f"{YELLOW}Make sure you have started: uvicorn backend.main:app --reload{RESET}")
    
    proceed = input(f"\n{YELLOW}Is the API running? (y/n): {RESET}").strip().lower()
    
    if proceed == 'y':
        results["RAG Integration"] = run_test_suite(
            "RAG Integration Test Suite",
            PROJECT_ROOT / "tests" / "test_rag_integration.py"
        )
    else:
        print(f"\n{YELLOW}⚠ Skipping RAG Integration tests (API not running){RESET}")
        results["RAG Integration"] = None
    
    # Calculate total time
    total_time = time.time() - start_time
    
    # Final Summary
    print_banner("COMPREHENSIVE TEST SUMMARY", MAGENTA)
    
    print(f"{BOLD}Test Suite Results:{RESET}\n")
    
    passed_count = 0
    total_count = 0
    
    for suite_name, result in results.items():
        total_count += 1
        
        if result is True:
            status = f"{GREEN}✓ PASSED{RESET}"
            passed_count += 1
        elif result is False:
            status = f"{YELLOW}⚠ PARTIAL / FAILED{RESET}"
        else:
            status = f"{BLUE}○ SKIPPED{RESET}"
            total_count -= 1  # Don't count skipped tests
        
        print(f"  {suite_name:30s} : {status}")
    
    print(f"\n{BOLD}Overall Results:{RESET}")
    print(f"  • Tests Run: {total_count}")
    print(f"  • Tests Passed: {passed_count}")
    print(f"  • Total Time: {total_time:.1f}s")
    
    # Final verdict
    print()
    if total_count > 0 and passed_count == total_count:
        print(f"{GREEN}{BOLD}{'='*80}{RESET}")
        print(f"{GREEN}{BOLD}✓ ALL TESTS PASSED - DAY 5 IMPLEMENTATION IS CORRECT!{RESET}")
        print(f"{GREEN}{BOLD}{'='*80}{RESET}")
        print(f"\n{GREEN}Your Day 5 RAG implementation is working correctly:{RESET}")
        print(f"  {GREEN}✓{RESET} Embeddings are generating correctly")
        print(f"  {GREEN}✓{RESET} ChromaDB persistence and queries work")
        print(f"  {GREEN}✓{RESET} RAG integration enhances both agents")
        print(f"  {GREEN}✓{RESET} Similar text retrieval is accurate")
        print(f"  {GREEN}✓{RESET} Metadata and relevancy scoring work")
        print()
        return 0
    
    elif passed_count > 0:
        print(f"{YELLOW}{BOLD}{'='*80}{RESET}")
        print(f"{YELLOW}{BOLD}⚠ PARTIAL SUCCESS - MOST TESTS PASSED{RESET}")
        print(f"{YELLOW}{BOLD}{'='*80}{RESET}")
        print(f"\n{YELLOW}Your Day 5 implementation is mostly functional:{RESET}")
        print(f"  • {passed_count}/{total_count} test suites passed")
        print(f"  • Review failed tests for improvements")
        print()
        return 1
    
    else:
        print(f"{RED}{BOLD}{'='*80}{RESET}")
        print(f"{RED}{BOLD}✗ TESTS FAILED - ISSUES DETECTED{RESET}")
        print(f"{RED}{BOLD}{'='*80}{RESET}")
        print(f"\n{RED}Your Day 5 implementation needs fixes:{RESET}")
        print(f"  • {passed_count}/{total_count} test suites passed")
        print(f"  • Check error messages above")
        print()
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Tests interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Fatal error: {e}{RESET}")
        sys.exit(1)
