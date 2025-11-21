"""
Test Suite 1: Embeddings Testing

Tests the embedding model (all-MiniLM-L6-v2) functionality:
- Similar text produces high similarity
- Different text produces low similarity
- Cosine similarity calculations
- Embedding dimensions and consistency
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from loguru import logger
from backend.vector_store import get_embedding_function

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'


def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors"""
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return dot_product / (norm1 * norm2)


def test_embedding_dimensions():
    """Test 1: Verify embedding dimensions are consistent"""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}Test 1: Embedding Dimensions and Consistency{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    try:
        embedding_fn = get_embedding_function()
        
        # Test different texts
        texts = [
            "Hello world",
            "This is a longer sentence about customer support and product issues.",
            "Short",
            "A" * 1000  # Very long text
        ]
        
        embeddings = []
        for text in texts:
            emb = embedding_fn([text])[0]
            embeddings.append(emb)
            print(f"Text: '{text[:50]}...' → Embedding shape: {len(emb)}")
        
        # Verify all embeddings have same dimension
        dimensions = [len(emb) for emb in embeddings]
        if len(set(dimensions)) == 1:
            print(f"\n{GREEN}✓ All embeddings have consistent dimension: {dimensions[0]}{RESET}")
            print(f"{GREEN}✓ Expected: 384 (all-MiniLM-L6-v2 standard){RESET}")
            
            if dimensions[0] == 384:
                print(f"{GREEN}{BOLD}✓ TEST 1 PASSED: Embedding dimensions correct (384){RESET}\n")
                return True
            else:
                print(f"{RED}{BOLD}✗ TEST 1 FAILED: Unexpected dimension {dimensions[0]}{RESET}\n")
                return False
        else:
            print(f"{RED}✗ Inconsistent dimensions: {dimensions}{RESET}")
            print(f"{RED}{BOLD}✗ TEST 1 FAILED: Dimension inconsistency{RESET}\n")
            return False
            
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        print(f"{RED}{BOLD}✗ TEST 1 FAILED: Exception occurred{RESET}\n")
        return False


def test_similar_text_high_similarity():
    """Test 2: Similar text should have high cosine similarity (>0.8)"""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}Test 2: Similar Text → High Similarity{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    try:
        embedding_fn = get_embedding_function()
        
        # Test pairs of similar texts
        similar_pairs = [
            (
                "My order hasn't arrived yet",
                "My package has not been delivered"
            ),
            (
                "I need to return this product",
                "I want to send back this item"
            ),
            (
                "The product is defective and broken",
                "This item is damaged and doesn't work"
            ),
            (
                "How do I track my shipment?",
                "Where can I check my delivery status?"
            ),
            (
                "Customer support contact information",
                "How to reach customer service"
            )
        ]
        
        print(f"{BOLD}Testing similar text pairs:{RESET}\n")
        
        all_passed = True
        similarities = []
        
        for i, (text1, text2) in enumerate(similar_pairs, 1):
            emb1 = embedding_fn([text1])[0]
            emb2 = embedding_fn([text2])[0]
            
            similarity = cosine_similarity(emb1, emb2)
            similarities.append(similarity)
            
            print(f"{BLUE}Pair {i}:{RESET}")
            print(f"  Text 1: '{text1}'")
            print(f"  Text 2: '{text2}'")
            print(f"  Similarity: {similarity:.4f}")
            
            if similarity > 0.8:
                print(f"  {GREEN}✓ High similarity (>0.8){RESET}\n")
            elif similarity > 0.6:
                print(f"  {YELLOW}⚠ Moderate similarity (0.6-0.8){RESET}\n")
                all_passed = False
            else:
                print(f"  {RED}✗ Low similarity (<0.6){RESET}\n")
                all_passed = False
        
        avg_similarity = sum(similarities) / len(similarities)
        print(f"\n{BOLD}Average similarity for similar pairs: {avg_similarity:.4f}{RESET}")
        
        if all_passed and avg_similarity > 0.8:
            print(f"{GREEN}{BOLD}✓ TEST 2 PASSED: Similar texts have high similarity (avg: {avg_similarity:.4f}){RESET}\n")
            return True
        elif avg_similarity > 0.7:
            print(f"{YELLOW}{BOLD}⚠ TEST 2 PARTIAL: Similar texts have moderate similarity (avg: {avg_similarity:.4f}){RESET}\n")
            return False
        else:
            print(f"{RED}{BOLD}✗ TEST 2 FAILED: Similar texts have low similarity (avg: {avg_similarity:.4f}){RESET}\n")
            return False
            
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        print(f"{RED}{BOLD}✗ TEST 2 FAILED: Exception occurred{RESET}\n")
        return False


def test_different_text_low_similarity():
    """Test 3: Different text should have low cosine similarity (<0.5)"""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}Test 3: Different Text → Low Similarity{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    try:
        embedding_fn = get_embedding_function()
        
        # Test pairs of different/unrelated texts
        different_pairs = [
            (
                "My order hasn't arrived yet",
                "The weather is sunny today"
            ),
            (
                "I need technical support for my laptop",
                "Recipe for chocolate cake with butter"
            ),
            (
                "Product return and refund policy",
                "History of ancient Roman architecture"
            ),
            (
                "Track my shipping package status",
                "Mathematical equations for quantum physics"
            ),
            (
                "Customer complaint about defective product",
                "Travel guide to Paris attractions"
            )
        ]
        
        print(f"{BOLD}Testing different text pairs:{RESET}\n")
        
        all_passed = True
        similarities = []
        
        for i, (text1, text2) in enumerate(different_pairs, 1):
            emb1 = embedding_fn([text1])[0]
            emb2 = embedding_fn([text2])[0]
            
            similarity = cosine_similarity(emb1, emb2)
            similarities.append(similarity)
            
            print(f"{BLUE}Pair {i}:{RESET}")
            print(f"  Text 1: '{text1}'")
            print(f"  Text 2: '{text2}'")
            print(f"  Similarity: {similarity:.4f}")
            
            if similarity < 0.3:
                print(f"  {GREEN}✓ Very low similarity (<0.3){RESET}\n")
            elif similarity < 0.5:
                print(f"  {GREEN}✓ Low similarity (<0.5){RESET}\n")
            elif similarity < 0.7:
                print(f"  {YELLOW}⚠ Moderate similarity (0.5-0.7){RESET}\n")
                all_passed = False
            else:
                print(f"  {RED}✗ High similarity (>0.7){RESET}\n")
                all_passed = False
        
        avg_similarity = sum(similarities) / len(similarities)
        print(f"\n{BOLD}Average similarity for different pairs: {avg_similarity:.4f}{RESET}")
        
        if all_passed and avg_similarity < 0.5:
            print(f"{GREEN}{BOLD}✓ TEST 3 PASSED: Different texts have low similarity (avg: {avg_similarity:.4f}){RESET}\n")
            return True
        elif avg_similarity < 0.7:
            print(f"{YELLOW}{BOLD}⚠ TEST 3 PARTIAL: Different texts have moderate similarity (avg: {avg_similarity:.4f}){RESET}\n")
            return False
        else:
            print(f"{RED}{BOLD}✗ TEST 3 FAILED: Different texts have high similarity (avg: {avg_similarity:.4f}){RESET}\n")
            return False
            
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        print(f"{RED}{BOLD}✗ TEST 3 FAILED: Exception occurred{RESET}\n")
        return False


def test_embedding_reproducibility():
    """Test 4: Same text should produce identical embeddings"""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}Test 4: Embedding Reproducibility{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    try:
        embedding_fn = get_embedding_function()
        
        text = "Test reproducibility with this exact sentence"
        
        # Generate embeddings multiple times
        embeddings = []
        for i in range(5):
            emb = embedding_fn([text])[0]
            embeddings.append(emb)
        
        print(f"Text: '{text}'")
        print(f"Generated embeddings {len(embeddings)} times\n")
        
        # Check if all embeddings are identical
        all_identical = True
        for i in range(1, len(embeddings)):
            if not np.allclose(embeddings[0], embeddings[i], rtol=1e-7):
                all_identical = False
                similarity = cosine_similarity(embeddings[0], embeddings[i])
                print(f"{YELLOW}⚠ Embedding {i+1} differs from embedding 1 (similarity: {similarity:.6f}){RESET}")
        
        if all_identical:
            print(f"{GREEN}✓ All embeddings are identical (deterministic){RESET}")
            print(f"{GREEN}{BOLD}✓ TEST 4 PASSED: Embeddings are reproducible{RESET}\n")
            return True
        else:
            print(f"{RED}✗ Embeddings are not identical{RESET}")
            print(f"{RED}{BOLD}✗ TEST 4 FAILED: Non-deterministic embeddings{RESET}\n")
            return False
            
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        print(f"{RED}{BOLD}✗ TEST 4 FAILED: Exception occurred{RESET}\n")
        return False


def run_all_tests():
    """Run all embedding tests"""
    print(f"\n{BOLD}{YELLOW}{'='*80}{RESET}")
    print(f"{BOLD}{YELLOW}EMBEDDING TEST SUITE{RESET}")
    print(f"{BOLD}{YELLOW}Testing: all-MiniLM-L6-v2 embedding model{RESET}")
    print(f"{BOLD}{YELLOW}{'='*80}{RESET}")
    
    results = {
        "Test 1: Embedding Dimensions": test_embedding_dimensions(),
        "Test 2: Similar Text High Similarity": test_similar_text_high_similarity(),
        "Test 3: Different Text Low Similarity": test_different_text_low_similarity(),
        "Test 4: Embedding Reproducibility": test_embedding_reproducibility()
    }
    
    # Summary
    print(f"\n{BOLD}{YELLOW}{'='*80}{RESET}")
    print(f"{BOLD}{YELLOW}EMBEDDING TEST SUMMARY{RESET}")
    print(f"{BOLD}{YELLOW}{'='*80}{RESET}\n")
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{GREEN}PASSED{RESET}" if result else f"{RED}FAILED{RESET}"
        print(f"{test_name}: {status}")
    
    print(f"\n{BOLD}Total: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"{GREEN}{BOLD}✓ ALL EMBEDDING TESTS PASSED{RESET}\n")
        return True
    else:
        print(f"{RED}{BOLD}✗ SOME EMBEDDING TESTS FAILED{RESET}\n")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
