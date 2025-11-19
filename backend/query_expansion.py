# backend/query_expansion.py
"""
Day 6: Query Expansion Module

Improves RAG retrieval by expanding user queries with:
- Synonyms and related terms
- Domain-specific keywords
- Multi-query generation for comprehensive retrieval

Production-level implementation with caching and performance optimization.
"""

from typing import List, Dict, Set, Optional
from loguru import logger
import re

# Domain-specific keyword mappings for e-commerce/support context
DOMAIN_KEYWORDS = {
    # Order/Purchase related
    "order": ["purchase", "transaction", "buy", "bought", "ordered"],
    "delivery": ["shipping", "shipment", "dispatch", "sent", "arrive", "received"],
    "return": ["refund", "exchange", "send back", "give back"],
    "cancel": ["abort", "stop", "terminate", "remove"],
    
    # Product related
    "product": ["item", "goods", "merchandise", "article"],
    "quality": ["condition", "state", "grade", "standard"],
    "price": ["cost", "rate", "fee", "charge", "pricing"],
    "discount": ["sale", "offer", "deal", "promotion", "coupon"],
    
    # Customer service
    "help": ["assist", "support", "aid", "service"],
    "issue": ["problem", "trouble", "difficulty", "concern"],
    "complaint": ["feedback", "dissatisfaction", "grievance"],
    "question": ["inquiry", "query", "ask", "clarification"],
    
    # Emotions/Sentiment
    "happy": ["satisfied", "pleased", "delighted", "content", "glad"],
    "unhappy": ["dissatisfied", "disappointed", "upset", "frustrated"],
    "urgent": ["immediate", "asap", "priority", "critical", "emergency"],
    
    # Content/Marketing
    "blog": ["article", "post", "content", "story", "write-up"],
    "marketing": ["promotion", "advertising", "campaign", "outreach"],
    "social": ["media", "platform", "network", "community"],
    "email": ["newsletter", "message", "communication", "correspondence"],
    
    # Quality descriptors
    "best": ["top", "excellent", "great", "superior", "premium"],
    "good": ["nice", "quality", "fine", "decent", "solid"],
    "bad": ["poor", "terrible", "awful", "inferior", "defective"],
    "fast": ["quick", "rapid", "speedy", "swift", "prompt"],
}

# Common stopwords to exclude from expansion
STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "should",
    "could", "may", "might", "can", "i", "you", "he", "she", "it", "we",
    "they", "my", "your", "his", "her", "its", "our", "their", "this",
    "that", "these", "those", "and", "or", "but", "if", "for", "to", "of",
    "in", "on", "at", "by", "with", "from", "as"
}


class QueryExpander:
    """
    Production-grade query expansion with caching and optimization
    """
    
    def __init__(self, enable_caching: bool = True, max_cache_size: int = 500):
        self.enable_caching = enable_caching
        self.max_cache_size = max_cache_size
        self._expansion_cache: Dict[str, List[str]] = {}
        logger.info(f"QueryExpander initialized (caching: {enable_caching})")
    
    def expand_query(
        self,
        query: str,
        max_expansions: int = 5,
        include_synonyms: bool = True,
        include_related: bool = True
    ) -> List[str]:
        """
        Expand a query into multiple variations
        
        Args:
            query: Original query text
            max_expansions: Maximum number of expanded queries to generate
            include_synonyms: Include synonym-based expansions
            include_related: Include related term expansions
        
        Returns:
            List of expanded query strings (includes original query)
        """
        # Check cache
        cache_key = f"{query}:{max_expansions}:{include_synonyms}:{include_related}"
        if self.enable_caching and cache_key in self._expansion_cache:
            logger.debug(f"Query expansion cache hit for: '{query[:50]}...'")
            return self._expansion_cache[cache_key]
        
        # Always include original query
        expanded_queries = [query]
        
        # Extract keywords from query
        keywords = self._extract_keywords(query)
        
        if not keywords:
            logger.debug(f"No expandable keywords found in query: '{query}'")
            return expanded_queries
        
        # Generate expansions
        if include_synonyms:
            synonym_queries = self._generate_synonym_expansions(query, keywords)
            expanded_queries.extend(synonym_queries[:max_expansions - len(expanded_queries)])
        
        if include_related and len(expanded_queries) < max_expansions:
            related_queries = self._generate_related_expansions(query, keywords)
            expanded_queries.extend(related_queries[:max_expansions - len(expanded_queries)])
        
        # Deduplicate while preserving order
        seen = set()
        unique_expanded = []
        for q in expanded_queries:
            q_lower = q.lower()
            if q_lower not in seen:
                seen.add(q_lower)
                unique_expanded.append(q)
        
        # Cache result
        if self.enable_caching:
            # Simple cache size management
            if len(self._expansion_cache) >= self.max_cache_size:
                # Remove oldest entry (first key)
                first_key = next(iter(self._expansion_cache))
                del self._expansion_cache[first_key]
            self._expansion_cache[cache_key] = unique_expanded
        
        logger.debug(f"Expanded query '{query[:40]}...' into {len(unique_expanded)} variants")
        return unique_expanded
    
    def _extract_keywords(self, query: str) -> List[str]:
        """
        Extract meaningful keywords from query
        
        Returns:
            List of keywords (lowercase, filtered)
        """
        # Tokenize (split on non-alphanumeric)
        tokens = re.findall(r'\b\w+\b', query.lower())
        
        # Filter stopwords and short tokens
        keywords = [
            token for token in tokens
            if token not in STOPWORDS and len(token) > 2
        ]
        
        return keywords
    
    def _generate_synonym_expansions(self, query: str, keywords: List[str]) -> List[str]:
        """
        Generate query variants using synonym replacement
        
        Strategy: Replace each keyword with its best synonym
        """
        expansions = []
        query_lower = query.lower()
        
        for keyword in keywords:
            # Check if keyword has domain synonyms
            synonyms = DOMAIN_KEYWORDS.get(keyword, [])
            
            if not synonyms:
                continue
            
            # Generate variants by replacing keyword with each synonym
            for synonym in synonyms[:2]:  # Limit to 2 synonyms per keyword
                # Case-insensitive replacement
                expanded = re.sub(
                    r'\b' + re.escape(keyword) + r'\b',
                    synonym,
                    query_lower,
                    flags=re.IGNORECASE
                )
                
                if expanded != query_lower:
                    expansions.append(expanded)
        
        return expansions
    
    def _generate_related_expansions(self, query: str, keywords: List[str]) -> List[str]:
        """
        Generate queries with related/contextual terms added
        
        Strategy: Append related terms to original query
        """
        expansions = []
        
        # Find all related terms for keywords in query
        related_terms = set()
        for keyword in keywords:
            if keyword in DOMAIN_KEYWORDS:
                # Add synonyms as related terms
                related_terms.update(DOMAIN_KEYWORDS[keyword][:3])
        
        # Generate expanded queries with related terms
        for term in list(related_terms)[:3]:  # Limit to 3 related expansions
            if term.lower() not in query.lower():
                expanded = f"{query} {term}"
                expansions.append(expanded)
        
        return expansions
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for monitoring"""
        return {
            "cache_size": len(self._expansion_cache),
            "max_cache_size": self.max_cache_size,
            "cache_enabled": self.enable_caching
        }
    
    def clear_cache(self):
        """Clear expansion cache"""
        self._expansion_cache.clear()
        logger.info("Query expansion cache cleared")


def expand_query_simple(query: str, max_expansions: int = 3) -> List[str]:
    """
    Simple query expansion without class instantiation (stateless)
    
    Args:
        query: Original query text
        max_expansions: Maximum number of expanded queries
    
    Returns:
        List of expanded queries (includes original)
    """
    expander = QueryExpander(enable_caching=False)
    return expander.expand_query(query, max_expansions=max_expansions)


def extract_keywords_from_query(query: str) -> List[str]:
    """
    Extract important keywords from query (utility function)
    
    Args:
        query: Query text
    
    Returns:
        List of extracted keywords
    """
    expander = QueryExpander(enable_caching=False)
    return expander._extract_keywords(query)


# Global expander instance for production use (with caching)
_global_expander: Optional[QueryExpander] = None


def get_query_expander() -> QueryExpander:
    """
    Get or create global query expander instance
    
    Returns:
        QueryExpander: Cached expander instance
    """
    global _global_expander
    
    if _global_expander is None:
        _global_expander = QueryExpander(enable_caching=True, max_cache_size=500)
        logger.info("Global QueryExpander initialized")
    
    return _global_expander
