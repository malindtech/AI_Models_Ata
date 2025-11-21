"""
Feedback-based Retrieval Re-ranker
Uses human feedback to improve RAG retrieval relevance over time
"""

import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
from loguru import logger


class FeedbackRanker:
    """
    Re-ranks retrieval results based on historical feedback patterns
    
    Learns from:
    - Which topics got approved vs rejected
    - Which retrieved contexts led to good content
    - Query-result pairs that worked well
    """
    
    def __init__(self, feedback_path: str = "data/human_feedback.csv"):
        self.feedback_path = Path(feedback_path)
        self.topic_scores = {}  # topic -> approval rate
        self.context_patterns = {}  # successful context patterns
        self._load_feedback_signals()
    
    def _load_feedback_signals(self):
        """Extract ranking signals from feedback data"""
        if not self.feedback_path.exists():
            logger.warning(f"Feedback file not found: {self.feedback_path}")
            return
        
        try:
            df = pd.read_csv(self.feedback_path)
            
            # Calculate topic success rates
            if 'topic' in df.columns and 'decision' in df.columns:
                for topic in df['topic'].unique():
                    topic_data = df[df['topic'] == topic]
                    approved = len(topic_data[topic_data['decision'] == 'approved'])
                    total = len(topic_data)
                    self.topic_scores[topic] = approved / total if total > 0 else 0.5
            
            logger.info(f"Loaded feedback signals: {len(self.topic_scores)} topics analyzed")
        
        except Exception as e:
            logger.error(f"Error loading feedback signals: {e}")
    
    def rerank_results(
        self, 
        results: List[Dict[str, Any]], 
        query: str,
        boost_factor: float = 0.2
    ) -> List[Dict[str, Any]]:
        """
        Re-rank retrieval results using feedback signals
        
        Args:
            results: List of retrieved documents with 'text', 'distance', 'metadata'
            query: Original user query
            boost_factor: How much to boost/penalize based on feedback (0-1)
        
        Returns:
            Re-ranked results list
        """
        if not results or not self.topic_scores:
            return results  # No feedback data yet
        
        # Score each result
        scored_results = []
        for result in results:
            base_score = 1.0 - result.get('distance', 0.5)  # Lower distance = higher score
            
            # Apply feedback boost
            feedback_boost = self._calculate_feedback_boost(result, query)
            adjusted_score = base_score * (1.0 + feedback_boost * boost_factor)
            
            scored_results.append({
                **result,
                'original_score': base_score,
                'feedback_boost': feedback_boost,
                'final_score': adjusted_score
            })
        
        # Sort by final score (descending)
        scored_results.sort(key=lambda x: x['final_score'], reverse=True)
        
        logger.info(f"Re-ranked {len(results)} results using feedback signals")
        return scored_results
    
    def _calculate_feedback_boost(self, result: Dict, query: str) -> float:
        """
        Calculate feedback-based boost for a result
        
        Returns value between -1.0 and 1.0:
        - Positive: Similar content was approved before
        - Negative: Similar content was rejected before
        - Zero: No feedback data
        """
        text = result.get('text', '').lower()
        metadata = result.get('metadata', {})
        
        # Check if result text matches successful topics
        boost = 0.0
        match_count = 0
        
        for topic, score in self.topic_scores.items():
            topic_lower = topic.lower()
            
            # Check if topic appears in result
            if topic_lower in text or topic_lower in str(metadata).lower():
                # Score ranges from 0 to 1, convert to -1 to 1
                topic_boost = (score - 0.5) * 2.0  # 0.5 -> 0, 1.0 -> 1.0, 0.0 -> -1.0
                boost += topic_boost
                match_count += 1
        
        # Average boost if multiple matches
        if match_count > 0:
            boost = boost / match_count
        
        return boost
    
    def get_ranking_stats(self) -> Dict:
        """Get statistics about learned ranking preferences"""
        if not self.topic_scores:
            return {"status": "no_feedback_data"}
        
        # Find best and worst performing topics
        sorted_topics = sorted(
            self.topic_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return {
            "total_topics": len(self.topic_scores),
            "top_performing": sorted_topics[:5],
            "bottom_performing": sorted_topics[-5:],
            "average_score": sum(self.topic_scores.values()) / len(self.topic_scores)
        }


# Singleton instance
_feedback_ranker = None

def get_feedback_ranker() -> FeedbackRanker:
    """Get or create feedback ranker instance"""
    global _feedback_ranker
    if _feedback_ranker is None:
        _feedback_ranker = FeedbackRanker()
    return _feedback_ranker


def apply_feedback_reranking(
    results: List[Dict[str, Any]], 
    query: str
) -> List[Dict[str, Any]]:
    """
    Convenience function to apply feedback-based re-ranking
    
    Usage:
        results = retrieve_from_db(query)
        reranked = apply_feedback_reranking(results, query)
    """
    ranker = get_feedback_ranker()
    return ranker.rerank_results(results, query)
