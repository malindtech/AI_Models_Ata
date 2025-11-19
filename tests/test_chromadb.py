"""
Test Suite 2: ChromaDB Testing

Tests ChromaDB persistence and query functionality:
- Insert data
- Query known text
- Verify relevancy (similarity scores)
- Verify persistence (restart and query)
- Check metadata
"""

import sys
from pathlib import Path
import time

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger
from backend.vector_store import (
    initialize_chroma_client,
    create_or_get_collection,
    add_documents,
    retrieve_similar
)

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'

# Test collection name
TEST_COLLECTION = "test_chromadb_suite"


def test_insert_data():
    """Test 1: Insert documents into ChromaDB"""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}Test 1: Insert Data into ChromaDB{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    try:
        # Initialize client
        client = initialize_chroma_client()
        print(f"{GREEN}✓ ChromaDB client initialized{RESET}\n")
        
        # Create test collection
        collection = create_or_get_collection(TEST_COLLECTION, client)
        print(f"{GREEN}✓ Test collection created: {TEST_COLLECTION}{RESET}\n")
        
        # Prepare test documents
        test_docs = [
            {
                "id": "doc1",
                "text": "My order hasn't arrived yet. It's been 2 weeks since I placed it.",
                "metadata": {"category": "shipping", "sentiment": "negative"}
            },
            {
                "id": "doc2",
                "text": "I want to return this product because it doesn't fit properly.",
                "metadata": {"category": "return", "sentiment": "neutral"}
            },
            {
                "id": "doc3",
                "text": "The product quality is excellent. Very satisfied with my purchase!",
                "metadata": {"category": "review", "sentiment": "positive"}
            },
            {
                "id": "doc4",
                "text": "How do I track my shipment? I need the tracking number.",
                "metadata": {"category": "inquiry", "sentiment": "neutral"}
            },
            {
                "id": "doc5",
                "text": "The item arrived damaged. I need a replacement immediately.",
                "metadata": {"category": "complaint", "sentiment": "negative"}
            },
            {
                "id": "doc6",
                "text": "What is your return policy? How many days do I have?",
                "metadata": {"category": "inquiry", "sentiment": "neutral"}
            },
            {
                "id": "doc7",
                "text": "I love this product! It works perfectly and exceeded my expectations.",
                "metadata": {"category": "review", "sentiment": "positive"}
            },
            {
                "id": "doc8",
                "text": "Can I change my shipping address? The order hasn't shipped yet.",
                "metadata": {"category": "inquiry", "sentiment": "neutral"}
            }
        ]
        
        print(f"{BOLD}Inserting {len(test_docs)} test documents:{RESET}")
        for doc in test_docs:
            print(f"  • ID: {doc['id']} | Category: {doc['metadata']['category']} | Sentiment: {doc['metadata']['sentiment']}")
            print(f"    Text: '{doc['text'][:60]}...'")
        
        # Insert documents
        success = add_documents(collection, test_docs)
        
        if success:
            # Verify insertion
            count = collection.count()
            print(f"\n{GREEN}✓ Documents inserted successfully{RESET}")
            print(f"{GREEN}✓ Collection count: {count} documents{RESET}")
            
            if count == len(test_docs):
                print(f"{GREEN}{BOLD}✓ TEST 1 PASSED: All {len(test_docs)} documents inserted{RESET}\n")
                return True, client
            else:
                print(f"{RED}✗ Count mismatch: expected {len(test_docs)}, got {count}{RESET}")
                print(f"{RED}{BOLD}✗ TEST 1 FAILED: Document count mismatch{RESET}\n")
                return False, client
        else:
            print(f"{RED}✗ Document insertion failed{RESET}")
            print(f"{RED}{BOLD}✗ TEST 1 FAILED: Insertion error{RESET}\n")
            return False, client
            
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        print(f"{RED}{BOLD}✗ TEST 1 FAILED: Exception occurred{RESET}\n")
        return False, None


def test_query_known_text(client):
    """Test 2: Query known text and verify retrieval"""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}Test 2: Query Known Text{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    try:
        if client is None:
            print(f"{RED}✗ No client available from Test 1{RESET}")
            print(f"{RED}{BOLD}✗ TEST 2 FAILED: Client initialization issue{RESET}\n")
            return False
        
        # Test queries with expected results
        test_queries = [
            {
                "query": "order not delivered",
                "expected_id": "doc1",
                "description": "Shipping delay query"
            },
            {
                "query": "want to return item",
                "expected_id": "doc2",
                "description": "Return request query"
            },
            {
                "query": "damaged product replacement",
                "expected_id": "doc5",
                "description": "Damaged item complaint"
            },
            {
                "query": "tracking number status",
                "expected_id": "doc4",
                "description": "Tracking inquiry"
            }
        ]
        
        print(f"{BOLD}Testing queries for known documents:{RESET}\n")
        
        all_passed = True
        
        for i, test in enumerate(test_queries, 1):
            print(f"{BLUE}Query {i}: {test['description']}{RESET}")
            print(f"  Query text: '{test['query']}'")
            print(f"  Expected document: {test['expected_id']}")
            
            # Retrieve results
            results = retrieve_similar(TEST_COLLECTION, test['query'], k=3, client=client)
            
            if not results:
                print(f"  {RED}✗ No results returned{RESET}\n")
                all_passed = False
                continue
            
            # Check if expected document is in top result
            top_result = results[0]
            print(f"  Top result: {top_result['id']} (distance: {top_result['distance']:.4f})")
            print(f"  Text: '{top_result['text'][:60]}...'")
            
            if top_result['id'] == test['expected_id']:
                print(f"  {GREEN}✓ Correct document retrieved{RESET}\n")
            else:
                print(f"  {RED}✗ Wrong document: expected {test['expected_id']}, got {top_result['id']}{RESET}\n")
                all_passed = False
        
        if all_passed:
            print(f"{GREEN}{BOLD}✓ TEST 2 PASSED: All known texts retrieved correctly{RESET}\n")
            return True
        else:
            print(f"{RED}{BOLD}✗ TEST 2 FAILED: Some queries returned wrong documents{RESET}\n")
            return False
            
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        print(f"{RED}{BOLD}✗ TEST 2 FAILED: Exception occurred{RESET}\n")
        return False


def test_verify_relevancy(client):
    """Test 3: Verify relevancy scores (similar queries have low distance)"""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}Test 3: Verify Relevancy Scores{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    try:
        if client is None:
            print(f"{RED}✗ No client available{RESET}")
            print(f"{RED}{BOLD}✗ TEST 3 FAILED: Client initialization issue{RESET}\n")
            return False
        
        # Test queries with relevancy expectations
        relevancy_tests = [
            {
                "query": "order delayed not arrived",
                "relevant_categories": ["shipping", "complaint"],
                "description": "Shipping issue - should find shipping/complaint docs"
            },
            {
                "query": "return refund policy",
                "relevant_categories": ["return", "inquiry"],
                "description": "Return inquiry - should find return/inquiry docs"
            },
            {
                "query": "excellent quality satisfied",
                "relevant_categories": ["review"],
                "description": "Positive review - should find review docs"
            }
        ]
        
        print(f"{BOLD}Testing relevancy scoring:{RESET}\n")
        
        all_passed = True
        
        for i, test in enumerate(relevancy_tests, 1):
            print(f"{BLUE}Relevancy Test {i}: {test['description']}{RESET}")
            print(f"  Query: '{test['query']}'")
            print(f"  Expected categories: {test['relevant_categories']}")
            
            # Retrieve top 3 results
            results = retrieve_similar(TEST_COLLECTION, test['query'], k=3, client=client)
            
            if not results:
                print(f"  {RED}✗ No results returned{RESET}\n")
                all_passed = False
                continue
            
            print(f"\n  Top 3 results:")
            relevant_count = 0
            
            for j, result in enumerate(results[:3], 1):
                distance = result['distance']
                category = result['metadata'].get('category', 'unknown')
                
                # Check if relevant
                is_relevant = category in test['relevant_categories']
                if is_relevant:
                    relevant_count += 1
                
                status = f"{GREEN}✓{RESET}" if is_relevant else f"{YELLOW}?{RESET}"
                print(f"    {j}. {status} ID: {result['id']} | Distance: {distance:.4f} | Category: {category}")
                print(f"       Text: '{result['text'][:60]}...'")
            
            # Check distance threshold (should be < 0.5 for relevant results)
            top_distance = results[0]['distance']
            
            print(f"\n  Analysis:")
            print(f"    • Relevant results in top 3: {relevant_count}/3")
            print(f"    • Top result distance: {top_distance:.4f}")
            
            if relevant_count >= 2 and top_distance < 0.6:
                print(f"  {GREEN}✓ Good relevancy (≥2 relevant, distance < 0.6){RESET}\n")
            elif relevant_count >= 1 and top_distance < 0.7:
                print(f"  {YELLOW}⚠ Moderate relevancy (≥1 relevant, distance < 0.7){RESET}\n")
                all_passed = False
            else:
                print(f"  {RED}✗ Poor relevancy{RESET}\n")
                all_passed = False
        
        if all_passed:
            print(f"{GREEN}{BOLD}✓ TEST 3 PASSED: Relevancy scores are good{RESET}\n")
            return True
        else:
            print(f"{YELLOW}{BOLD}⚠ TEST 3 PARTIAL: Some relevancy issues{RESET}\n")
            return False
            
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        print(f"{RED}{BOLD}✗ TEST 3 FAILED: Exception occurred{RESET}\n")
        return False


def test_verify_persistence():
    """Test 4: Verify persistence - reinitialize client and query again"""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}Test 4: Verify Persistence{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    try:
        print(f"{BOLD}Simulating restart by reinitializing client...{RESET}\n")
        
        # Force new client by clearing cache
        from backend import vector_store
        vector_store._chroma_client = None
        
        # Initialize new client
        new_client = initialize_chroma_client()
        print(f"{GREEN}✓ New ChromaDB client initialized{RESET}\n")
        
        # Try to retrieve collection
        collection = create_or_get_collection(TEST_COLLECTION, new_client)
        count = collection.count()
        
        print(f"Collection '{TEST_COLLECTION}' count: {count} documents")
        
        if count == 8:  # Expected from Test 1
            print(f"{GREEN}✓ All documents persisted correctly{RESET}\n")
        else:
            print(f"{YELLOW}⚠ Document count mismatch: expected 8, got {count}{RESET}\n")
        
        # Test query on persisted data
        print(f"{BOLD}Testing query on persisted data:{RESET}")
        query = "order not delivered"
        print(f"  Query: '{query}'")
        
        results = retrieve_similar(TEST_COLLECTION, query, k=3, client=new_client)
        
        if results:
            top_result = results[0]
            print(f"  Top result: {top_result['id']}")
            print(f"  Distance: {top_result['distance']:.4f}")
            print(f"  Text: '{top_result['text'][:60]}...'")
            
            if top_result['id'] == "doc1" and count == 8:
                print(f"\n{GREEN}✓ Persistence verified: correct document retrieved{RESET}")
                print(f"{GREEN}{BOLD}✓ TEST 4 PASSED: Data persisted correctly{RESET}\n")
                return True, new_client
            else:
                print(f"\n{YELLOW}⚠ Persistence partial: data exists but query mismatch{RESET}")
                print(f"{YELLOW}{BOLD}⚠ TEST 4 PARTIAL: Some persistence issues{RESET}\n")
                return False, new_client
        else:
            print(f"\n{RED}✗ No results from query{RESET}")
            print(f"{RED}{BOLD}✗ TEST 4 FAILED: Query failed on persisted data{RESET}\n")
            return False, new_client
            
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        print(f"{RED}{BOLD}✗ TEST 4 FAILED: Exception occurred{RESET}\n")
        return False, None


def test_check_metadata(client):
    """Test 5: Check metadata retrieval and filtering"""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}Test 5: Check Metadata{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    try:
        if client is None:
            print(f"{RED}✗ No client available{RESET}")
            print(f"{RED}{BOLD}✗ TEST 5 FAILED: Client initialization issue{RESET}\n")
            return False
        
        print(f"{BOLD}Testing metadata retrieval:{RESET}\n")
        
        # Query and check metadata
        query = "product quality"
        print(f"Query: '{query}'")
        
        results = retrieve_similar(TEST_COLLECTION, query, k=5, client=client)
        
        if not results:
            print(f"{RED}✗ No results returned{RESET}")
            print(f"{RED}{BOLD}✗ TEST 5 FAILED: No results{RESET}\n")
            return False
        
        print(f"\nResults with metadata:\n")
        
        metadata_complete = True
        
        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            category = metadata.get('category', None)
            sentiment = metadata.get('sentiment', None)
            
            print(f"{i}. ID: {result['id']}")
            print(f"   Distance: {result['distance']:.4f}")
            print(f"   Category: {category}")
            print(f"   Sentiment: {sentiment}")
            print(f"   Text: '{result['text'][:60]}...'")
            
            if category is None or sentiment is None:
                print(f"   {RED}✗ Missing metadata{RESET}")
                metadata_complete = False
            else:
                print(f"   {GREEN}✓ Metadata complete{RESET}")
            
            print()
        
        # Test metadata-based analysis
        print(f"{BOLD}Metadata analysis:{RESET}")
        categories = [r.get('metadata', {}).get('category') for r in results]
        sentiments = [r.get('metadata', {}).get('sentiment') for r in results]
        
        print(f"  Categories found: {set(categories)}")
        print(f"  Sentiments found: {set(sentiments)}")
        
        if metadata_complete and len(categories) > 0:
            print(f"\n{GREEN}✓ All metadata retrieved successfully{RESET}")
            print(f"{GREEN}{BOLD}✓ TEST 5 PASSED: Metadata working correctly{RESET}\n")
            return True
        else:
            print(f"\n{RED}✗ Some metadata missing or incomplete{RESET}")
            print(f"{RED}{BOLD}✗ TEST 5 FAILED: Metadata issues{RESET}\n")
            return False
            
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        print(f"{RED}{BOLD}✗ TEST 5 FAILED: Exception occurred{RESET}\n")
        return False


def cleanup_test_collection(client):
    """Clean up test collection"""
    try:
        if client is not None:
            client.delete_collection(TEST_COLLECTION)
            print(f"{GREEN}✓ Test collection cleaned up{RESET}")
    except Exception as e:
        print(f"{YELLOW}⚠ Cleanup warning: {e}{RESET}")


def run_all_tests():
    """Run all ChromaDB tests"""
    print(f"\n{BOLD}{YELLOW}{'='*80}{RESET}")
    print(f"{BOLD}{YELLOW}CHROMADB TEST SUITE{RESET}")
    print(f"{BOLD}{YELLOW}Testing: ChromaDB persistence and query functionality{RESET}")
    print(f"{BOLD}{YELLOW}{'='*80}{RESET}")
    
    results = {}
    client = None
    
    # Test 1: Insert data
    test1_result, client = test_insert_data()
    results["Test 1: Insert Data"] = test1_result
    
    if client:
        # Test 2: Query known text
        results["Test 2: Query Known Text"] = test_query_known_text(client)
        
        # Test 3: Verify relevancy
        results["Test 3: Verify Relevancy"] = test_verify_relevancy(client)
    else:
        results["Test 2: Query Known Text"] = False
        results["Test 3: Verify Relevancy"] = False
    
    # Test 4: Verify persistence (creates new client)
    test4_result, new_client = test_verify_persistence()
    results["Test 4: Verify Persistence"] = test4_result
    
    if new_client:
        # Test 5: Check metadata
        results["Test 5: Check Metadata"] = test_check_metadata(new_client)
        
        # Cleanup
        cleanup_test_collection(new_client)
    else:
        results["Test 5: Check Metadata"] = False
    
    # Summary
    print(f"\n{BOLD}{YELLOW}{'='*80}{RESET}")
    print(f"{BOLD}{YELLOW}CHROMADB TEST SUMMARY{RESET}")
    print(f"{BOLD}{YELLOW}{'='*80}{RESET}\n")
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{GREEN}PASSED{RESET}" if result else f"{RED}FAILED{RESET}"
        print(f"{test_name}: {status}")
    
    print(f"\n{BOLD}Total: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"{GREEN}{BOLD}✓ ALL CHROMADB TESTS PASSED{RESET}\n")
        return True
    elif passed >= 3:
        print(f"{YELLOW}{BOLD}⚠ MOST CHROMADB TESTS PASSED ({passed}/{total}){RESET}\n")
        return True
    else:
        print(f"{RED}{BOLD}✗ MANY CHROMADB TESTS FAILED{RESET}\n")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
