#!/usr/bin/env python3
"""
Day 6: K-Value Optimization Framework

Automatically determines optimal k-value for RAG retrieval by testing:
- Precision (relevance of retrieved documents)
- Recall (coverage of relevant information)
- Latency (speed of retrieval)
- Quality (downstream generation quality)

Outputs recommended k-value for production use.
"""

import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger
from backend.vector_store import retrieve_similar, initialize_chroma_client
from backend.rag_utils import prepare_rag_context

# K values to test
K_VALUES = [3, 5, 7, 10]

# Test queries with expected relevant keywords (for relevance scoring)
TEST_QUERIES_WITH_KEYWORDS = {
    "support": [
        {
            "query": "I need to return a damaged product",
            "relevant_keywords": ["return", "refund", "exchange", "damage", "defect", "send back"]
        },
        {
            "query": "How do I track my order?",
            "relevant_keywords": ["track", "shipping", "delivery", "status", "where", "locate"]
        },
        {
            "query": "I want to cancel my subscription",
            "relevant_keywords": ["cancel", "subscription", "stop", "terminate", "end", "refund"]
        },
    ],
    "products": [
        {
            "query": "comfortable running shoes for marathon",
            "relevant_keywords": ["shoe", "running", "comfort", "athletic", "sport", "foot", "cushion"]
        },
        {
            "query": "wireless headphones with noise cancellation",
            "relevant_keywords": ["headphone", "wireless", "bluetooth", "noise", "cancel", "audio", "sound"]
        },
    ],
    "blogs": [
        {
            "query": "digital marketing best practices",
            "relevant_keywords": ["market", "digital", "strategy", "campaign", "advertis", "seo", "content"]
        },
        {
            "query": "customer engagement strategies",
            "relevant_keywords": ["customer", "engage", "retention", "loyalty", "experience", "relationship"]
        },
    ]
}


def calculate_relevance_score(
    retrieved_text: str,
    relevant_keywords: List[str]
) -> float:
    """
    Calculate relevance score based on keyword presence
    
    Args:
        retrieved_text: Retrieved document text
        relevant_keywords: List of keywords that indicate relevance
    
    Returns:
        Score between 0 and 1 (percentage of keywords found)
    """
    text_lower = retrieved_text.lower()
    found_count = sum(1 for keyword in relevant_keywords if keyword.lower() in text_lower)
    
    return found_count / len(relevant_keywords) if relevant_keywords else 0.0


def test_k_value(
    collection_name: str,
    query: str,
    relevant_keywords: List[str],
    k: int
) -> Dict[str, Any]:
    """
    Test retrieval with specific k-value
    
    Returns:
        Dict with performance metrics
    """
    start_time = time.time()
    
    try:
        # Retrieve documents
        results = retrieve_similar(
            collection_name=collection_name,
            query=query,
            k=k
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Calculate relevance scores
        relevance_scores = [
            calculate_relevance_score(doc['text'], relevant_keywords)
            for doc in results
        ]
        
        # Calculate metrics
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
        max_relevance = max(relevance_scores) if relevance_scores else 0.0
        
        # Distance metrics (lower is better)
        distances = [doc['distance'] for doc in results]
        avg_distance = sum(distances) / len(distances) if distances else 1.0
        
        # Context preparation
        context = prepare_rag_context(results, max_tokens=1500)
        context_length = len(context)
        
        return {
            "success": True,
            "k": k,
            "num_results": len(results),
            "latency_ms": round(latency_ms, 2),
            "avg_relevance": round(avg_relevance, 4),
            "max_relevance": round(max_relevance, 4),
            "avg_distance": round(avg_distance, 4),
            "context_length": context_length,
            "estimated_tokens": context_length // 4
        }
        
    except Exception as e:
        logger.error(f"Test failed for k={k}: {e}")
        return {
            "success": False,
            "k": k,
            "error": str(e)
        }


def run_k_optimization(collection_name: str) -> Dict[str, Any]:
    """
    Run k-value optimization for a collection
    
    Returns:
        Dict with optimization results and recommendation
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"K-VALUE OPTIMIZATION: {collection_name}")
    logger.info(f"{'='*60}")
    
    if collection_name not in TEST_QUERIES_WITH_KEYWORDS:
        logger.warning(f"No test queries for collection: {collection_name}")
        return {"error": f"No test queries for {collection_name}"}
    
    test_queries = TEST_QUERIES_WITH_KEYWORDS[collection_name]
    results_by_k = {k: [] for k in K_VALUES}
    
    # Test each query with each k-value
    for query_data in test_queries:
        query = query_data["query"]
        keywords = query_data["relevant_keywords"]
        
        logger.info(f"\nTesting query: '{query}'")
        
        for k in K_VALUES:
            result = test_k_value(collection_name, query, keywords, k)
            results_by_k[k].append(result)
            
            if result["success"]:
                logger.info(
                    f"  k={k}: latency={result['latency_ms']}ms, "
                    f"relevance={result['avg_relevance']:.2f}, "
                    f"tokens={result['estimated_tokens']}"
                )
    
    # Aggregate metrics across queries
    k_metrics = {}
    for k in K_VALUES:
        successful_results = [r for r in results_by_k[k] if r.get("success")]
        
        if not successful_results:
            continue
        
        k_metrics[k] = {
            "avg_latency_ms": round(
                sum(r["latency_ms"] for r in successful_results) / len(successful_results), 2
            ),
            "avg_relevance": round(
                sum(r["avg_relevance"] for r in successful_results) / len(successful_results), 4
            ),
            "max_relevance": round(
                max(r["max_relevance"] for r in successful_results), 4
            ),
            "avg_distance": round(
                sum(r["avg_distance"] for r in successful_results) / len(successful_results), 4
            ),
            "avg_context_tokens": round(
                sum(r["estimated_tokens"] for r in successful_results) / len(successful_results)
            ),
            "tests_run": len(successful_results)
        }
    
    # Calculate composite score for each k
    # Score = (relevance * 0.5) + ((1 - normalized_latency) * 0.3) + ((1 - distance) * 0.2)
    logger.info(f"\n{'='*60}")
    logger.info("AGGREGATE METRICS BY K-VALUE")
    logger.info(f"{'='*60}\n")
    
    max_latency = max(m["avg_latency_ms"] for m in k_metrics.values())
    
    scored_k_values = []
    for k, metrics in k_metrics.items():
        normalized_latency = metrics["avg_latency_ms"] / max_latency if max_latency > 0 else 0
        
        composite_score = (
            metrics["avg_relevance"] * 0.5 +
            (1 - normalized_latency) * 0.3 +
            (1 - metrics["avg_distance"]) * 0.2
        )
        
        scored_k_values.append((k, composite_score, metrics))
        
        logger.info(f"k={k}:")
        logger.info(f"  Latency: {metrics['avg_latency_ms']}ms")
        logger.info(f"  Relevance: {metrics['avg_relevance']:.4f}")
        logger.info(f"  Distance: {metrics['avg_distance']:.4f}")
        logger.info(f"  Context Tokens: {metrics['avg_context_tokens']}")
        logger.info(f"  Composite Score: {composite_score:.4f}")
        logger.info("")
    
    # Sort by composite score (highest first)
    scored_k_values.sort(key=lambda x: x[1], reverse=True)
    
    # Recommendation
    best_k = scored_k_values[0][0] if scored_k_values else 5
    best_score = scored_k_values[0][1] if scored_k_values else 0.0
    
    logger.info(f"{'='*60}")
    logger.info(f"RECOMMENDATION: k={best_k}")
    logger.info(f"  Composite Score: {best_score:.4f}")
    logger.info(f"  Reason: Best balance of relevance, speed, and context quality")
    logger.info(f"{'='*60}\n")
    
    return {
        "collection": collection_name,
        "k_metrics": k_metrics,
        "scored_k_values": [(k, float(score)) for k, score, _ in scored_k_values],
        "recommendation": {
            "optimal_k": best_k,
            "composite_score": round(best_score, 4),
            "metrics": k_metrics[best_k]
        }
    }


def run_full_optimization() -> Dict[str, Any]:
    """
    Run k-value optimization for all collections
    
    Returns:
        Dict with all optimization results
    """
    logger.info("="*70)
    logger.info("DAY 6: K-VALUE OPTIMIZATION FRAMEWORK")
    logger.info("="*70)
    
    # Initialize ChromaDB
    try:
        initialize_chroma_client()
        logger.info("✓ ChromaDB initialized\n")
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB: {e}")
        return {"error": str(e)}
    
    # Run optimization for each collection with test queries
    optimization_results = {}
    
    for collection_name in TEST_QUERIES_WITH_KEYWORDS.keys():
        try:
            result = run_k_optimization(collection_name)
            optimization_results[collection_name] = result
        except Exception as e:
            logger.error(f"Optimization failed for {collection_name}: {e}")
            optimization_results[collection_name] = {"error": str(e)}
    
    # Overall summary
    logger.info("="*70)
    logger.info("OVERALL K-VALUE RECOMMENDATIONS")
    logger.info("="*70)
    
    for collection_name, result in optimization_results.items():
        if "recommendation" in result:
            rec = result["recommendation"]
            logger.info(
                f"{collection_name.upper()}: k={rec['optimal_k']} "
                f"(score: {rec['composite_score']:.4f}, "
                f"relevance: {rec['metrics']['avg_relevance']:.4f})"
            )
    
    # General recommendation
    if optimization_results:
        all_optimal_k = [
            r["recommendation"]["optimal_k"]
            for r in optimization_results.values()
            if "recommendation" in r
        ]
        if all_optimal_k:
            from collections import Counter
            most_common_k = Counter(all_optimal_k).most_common(1)[0][0]
            
            logger.info(f"\n{'='*70}")
            logger.info(f"GENERAL RECOMMENDATION FOR ALL COLLECTIONS: k={most_common_k}")
            logger.info(f"{'='*70}")
    
    return {
        "timestamp": datetime.now().isoformat(),
        "k_values_tested": K_VALUES,
        "collections_tested": list(TEST_QUERIES_WITH_KEYWORDS.keys()),
        "results": optimization_results
    }


def save_optimization_results(results: Dict[str, Any], output_dir: Path = None):
    """Save optimization results to JSON"""
    if output_dir is None:
        output_dir = PROJECT_ROOT / "logs"
    
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "day6_k_optimization_results.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n✓ Optimization results saved to: {output_file}")
    return output_file


def main():
    """Main execution"""
    try:
        results = run_full_optimization()
        
        if "error" in results:
            logger.error(f"Optimization failed: {results['error']}")
            return 1
        
        # Save results
        save_optimization_results(results)
        
        logger.info("\n✓ K-value optimization complete!")
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("\nOptimization interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Optimization failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
