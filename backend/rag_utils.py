# backend/rag_utils.py
"""
RAG (Retrieval-Augmented Generation) Utilities

Helper functions for integrating retrieved context into prompts:
- Context formatting and truncation
- Prompt injection
- Token estimation
- Duplicate filtering

Day 6 Enhancements:
- Query expansion integration
- Personalization support
- Enhanced retrieval with re-ranking

Day 8 Enhancements:
- Semantic similarity-based hallucination detection
- Embedding-based content verification
"""

from typing import List, Dict, Any, Optional
from loguru import logger
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Lazy load embedding model to avoid startup overhead
_embedding_model = None

def get_embedding_model():
    """Lazy-load sentence transformer model for semantic similarity"""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Loaded sentence transformer model for semantic similarity")
    return _embedding_model


def calculate_token_estimate(text: str) -> int:
    """
    Rough token estimation: 1 token ≈ 4 characters
    
    Args:
        text: Input text
        
    Returns:
        Estimated token count
    """
    return len(text) // 4


def format_retrieved_context(
    documents: List[Dict[str, Any]],
    max_tokens: int = 1500,
    include_metadata: bool = False
) -> str:
    """
    Format retrieved documents into a context string
    
    Args:
        documents: List of dicts with 'text' and optional 'metadata'
        max_tokens: Maximum tokens for total context
        include_metadata: Whether to include metadata in context
        
    Returns:
        Formatted context string
        
    Format:
        Context 1:
        {text}
        
        Context 2:
        {text}
        ...
    """
    if not documents:
        return ""
    
    formatted_parts = []
    current_tokens = 0
    
    for i, doc in enumerate(documents, 1):
        text = doc.get('text', '')
        
        # Build context entry
        if include_metadata and 'metadata' in doc:
            metadata = doc['metadata']
            # Format key metadata fields
            meta_str = ", ".join([f"{k}: {v}" for k, v in metadata.items() if k != '_collection'])
            entry = f"Context {i} ({meta_str}):\n{text}"
        else:
            entry = f"Context {i}:\n{text}"
        
        entry_tokens = calculate_token_estimate(entry)
        
        # Check if adding this would exceed limit
        if current_tokens + entry_tokens > max_tokens:
            # Truncate the text to fit
            remaining_tokens = max_tokens - current_tokens - 20  # Buffer for "Context N:"
            if remaining_tokens > 50:  # Only add if meaningful content fits
                remaining_chars = remaining_tokens * 4
                truncated_text = text[:remaining_chars] + "..."
                if include_metadata and 'metadata' in doc:
                    entry = f"Context {i} ({meta_str}):\n{truncated_text}"
                else:
                    entry = f"Context {i}:\n{truncated_text}"
                formatted_parts.append(entry)
            break
        
        formatted_parts.append(entry)
        current_tokens += entry_tokens
    
    context = "\n\n".join(formatted_parts)
    logger.debug(f"Formatted {len(formatted_parts)} contexts (~{current_tokens} tokens)")
    
    return context


def inject_rag_context(base_prompt: str, context: str) -> str:
    """
    Inject retrieved context into base prompt
    
    Strategy: Add context section after system instructions but before user query
    
    Args:
        base_prompt: Original prompt template
        context: Formatted retrieved context
        
    Returns:
        Enhanced prompt with context
        
    Template:
        {system_instructions}
        
        Relevant Context from Similar Cases:
        {context}
        
        {user_query}
    """
    if not context or not context.strip():
        return base_prompt
    
    # Add context section
    context_section = f"\n\nRelevant Context from Similar Cases:\n{context}\n\nBased on the above context and the query below, provide your response:\n"
    
    # Inject context into prompt
    # Simple injection: add after first paragraph (system instructions)
    lines = base_prompt.split('\n\n', 1)
    
    if len(lines) == 2:
        # Has system instructions + query
        enhanced_prompt = lines[0] + context_section + lines[1]
    else:
        # Single block - add context at beginning
        enhanced_prompt = context_section + base_prompt
    
    logger.debug(f"Injected context ({len(context)} chars) into prompt")
    return enhanced_prompt


def filter_duplicate_contexts(documents: List[Dict[str, Any]], similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
    """
    Remove near-duplicate documents based on text overlap
    
    Args:
        documents: List of document dicts
        similarity_threshold: Jaccard similarity threshold (0-1)
        
    Returns:
        Filtered list of documents
    """
    if not documents:
        return []
    
    def get_word_set(text: str) -> set:
        """Get set of lowercase words"""
        return set(text.lower().split())
    
    def jaccard_similarity(set1: set, set2: set) -> float:
        """Calculate Jaccard similarity between two sets"""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
    
    filtered = []
    seen_word_sets = []
    
    for doc in documents:
        text = doc.get('text', '')
        word_set = get_word_set(text)
        
        # Check against already added documents
        is_duplicate = False
        for seen_set in seen_word_sets:
            similarity = jaccard_similarity(word_set, seen_set)
            if similarity >= similarity_threshold:
                is_duplicate = True
                break
        
        if not is_duplicate:
            filtered.append(doc)
            seen_word_sets.append(word_set)
    
    if len(filtered) < len(documents):
        logger.debug(f"Filtered {len(documents) - len(filtered)} duplicate contexts")
    
    return filtered


def truncate_context_by_relevance(
    documents: List[Dict[str, Any]],
    max_contexts: int = 5,
    distance_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Truncate contexts based on relevance score (distance)
    
    Args:
        documents: List of document dicts with 'distance' field
        max_contexts: Maximum number of contexts to keep
        distance_threshold: Maximum distance (lower is more relevant)
        
    Returns:
        Filtered list of most relevant documents
    """
    # Filter by distance threshold
    relevant = [doc for doc in documents if doc.get('distance', 1.0) <= distance_threshold]
    
    # Take top-k by relevance
    relevant = relevant[:max_contexts]
    
    if len(relevant) < len(documents):
        logger.debug(f"Truncated to {len(relevant)} most relevant contexts (threshold: {distance_threshold})")
    
    return relevant


def prepare_rag_context(
    documents: List[Dict[str, Any]],
    max_tokens: int = 1500,
    max_contexts: int = 5,
    distance_threshold: float = 0.7,
    filter_duplicates: bool = True
) -> str:
    """
    Complete RAG context preparation pipeline
    
    Args:
        documents: Retrieved documents
        max_tokens: Maximum tokens for context
        max_contexts: Maximum number of contexts
        distance_threshold: Relevance threshold
        filter_duplicates: Whether to filter duplicate contexts
        
    Returns:
        Formatted, filtered context string ready for injection
    """
    if not documents:
        return ""
    
    # Step 1: Truncate by relevance
    filtered = truncate_context_by_relevance(documents, max_contexts, distance_threshold)
    
    # Step 2: Remove duplicates
    if filter_duplicates:
        filtered = filter_duplicate_contexts(filtered)
    
    # Step 3: Format with token limit
    context = format_retrieved_context(filtered, max_tokens)
    
    logger.info(f"Prepared RAG context: {len(filtered)} docs -> {calculate_token_estimate(context)} tokens")
    
    return context


# ============================================================================
# DAY 6: ENHANCED RAG FUNCTIONS
# ============================================================================

def retrieve_with_query_expansion(
    collection_name: str,
    query: str,
    k: int = 5,
    enable_expansion: bool = True,
    max_expansions: int = 3
) -> List[Dict[str, Any]]:
    """
    Retrieve documents with optional query expansion
    
    Day 6 Enhancement: Expands query to improve recall
    
    Args:
        collection_name: Collection to search
        query: Original query
        k: Number of results to return
        enable_expansion: Whether to use query expansion
        max_expansions: Maximum number of expanded queries
    
    Returns:
        List of retrieved documents (deduplicated)
    """
    try:
        from backend.vector_store import retrieve_similar
        from backend.query_expansion import get_query_expander
    except ImportError as e:
        logger.error(f"Failed to import dependencies: {e}")
        return []
    
    if not enable_expansion:
        # Standard retrieval without expansion
        return retrieve_similar(collection_name, query, k)
    
    # Expand query
    expander = get_query_expander()
    expanded_queries = expander.expand_query(
        query,
        max_expansions=max_expansions,
        include_synonyms=True,
        include_related=True
    )
    
    logger.debug(f"Query expanded into {len(expanded_queries)} variants")
    
    # Retrieve with each expanded query
    all_results = []
    seen_ids = set()
    
    for exp_query in expanded_queries:
        try:
            results = retrieve_similar(collection_name, exp_query, k=k)
            
            # Deduplicate by ID
            for doc in results:
                doc_id = doc.get('id')
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    all_results.append(doc)
        except Exception as e:
            logger.warning(f"Retrieval failed for expanded query '{exp_query}': {e}")
            continue
    
    # Sort by distance (best first) and limit to k * 2
    all_results.sort(key=lambda x: x.get('distance', 1.0))
    limited_results = all_results[:k * 2]
    
    logger.info(f"Query expansion retrieved {len(limited_results)} unique documents from {len(expanded_queries)} queries")
    
    return limited_results


def prepare_rag_context_enhanced(
    documents: List[Dict[str, Any]],
    max_tokens: int = 1500,
    max_contexts: int = 5,
    distance_threshold: float = 0.7,
    filter_duplicates: bool = True,
    personalization_context: Optional[Dict[str, str]] = None
) -> str:
    """
    Enhanced RAG context preparation with Day 6 improvements
    
    Day 6 Enhancements:
    - Query expansion integration (via retrieve_with_query_expansion)
    - Personalization token support
    - Improved relevance filtering
    
    Args:
        documents: Retrieved documents
        max_tokens: Maximum tokens for context
        max_contexts: Maximum number of contexts
        distance_threshold: Relevance threshold
        filter_duplicates: Whether to filter duplicate contexts
        personalization_context: Optional context for personalization
    
    Returns:
        Formatted, filtered, personalized context string
    """
    if not documents:
        return ""
    
    # Step 1: Truncate by relevance
    filtered = truncate_context_by_relevance(documents, max_contexts, distance_threshold)
    
    # Step 2: Remove duplicates
    if filter_duplicates:
        filtered = filter_duplicate_contexts(filtered)
    
    # Step 3: Format with token limit
    context = format_retrieved_context(filtered, max_tokens)
    
    # Step 4: Personalize if context provided (Day 6)
    if personalization_context and context:
        try:
            from backend.personalization import personalize_content
            context = personalize_content(context, personalization_context, strict=False)
            logger.debug("Applied personalization to RAG context")
        except ImportError:
            logger.warning("Personalization module not available")
        except Exception as e:
            logger.error(f"Personalization failed: {e}")
    
    logger.info(f"Prepared enhanced RAG context: {len(filtered)} docs -> {calculate_token_estimate(context)} tokens")
    
    return context


def inject_rag_context_with_personalization(
    base_prompt: str,
    context: str,
    personalization_context: Optional[Dict[str, str]] = None
) -> str:
    """
    Inject RAG context and apply personalization to full prompt
    
    Day 6 Enhancement: Personalizes both context and prompt
    
    Args:
        base_prompt: Original prompt template
        context: Retrieved context
        personalization_context: Optional personalization values
    
    Returns:
        Enhanced and personalized prompt
    """
    # First inject context
    enhanced_prompt = inject_rag_context(base_prompt, context)
    
    # Then personalize entire prompt if context provided
    if personalization_context:
        try:
            from backend.personalization import personalize_content
            enhanced_prompt = personalize_content(enhanced_prompt, personalization_context, strict=False)
            logger.debug("Applied personalization to full prompt")
        except ImportError:
            logger.warning("Personalization module not available")
        except Exception as e:
            logger.error(f"Prompt personalization failed: {e}")
    
    return enhanced_prompt


def hybrid_retrieve_and_rank(
    collection_name: str,
    query: str,
    k: int = 5,
    enable_expansion: bool = True,
    rerank_by_keywords: bool = True
) -> List[Dict[str, Any]]:
    """
    Hybrid retrieval with semantic search + keyword re-ranking
    
    Day 6 Enhancement: Combines semantic and lexical matching
    
    Args:
        collection_name: Collection to search
        query: Search query
        k: Number of results
        enable_expansion: Use query expansion
        rerank_by_keywords: Apply keyword-based re-ranking
    
    Returns:
        Retrieved and re-ranked documents
    """
    # Retrieve with optional expansion
    results = retrieve_with_query_expansion(
        collection_name,
        query,
        k=k * 2,  # Get more results for re-ranking
        enable_expansion=enable_expansion
    )
    
    if not rerank_by_keywords or not results:
        return results[:k]
    
    # Extract query keywords for re-ranking
    try:
        from backend.query_expansion import extract_keywords_from_query
        query_keywords = extract_keywords_from_query(query)
    except ImportError:
        logger.warning("Query expansion module not available for re-ranking")
        return results[:k]
    
    if not query_keywords:
        return results[:k]
    
    # Re-rank by keyword overlap
    for doc in results:
        text_lower = doc.get('text', '').lower()
        keyword_score = sum(1 for kw in query_keywords if kw.lower() in text_lower)
        keyword_score_normalized = keyword_score / len(query_keywords) if query_keywords else 0
        
        # Combine semantic distance with keyword score
        # Lower distance is better (more similar)
        # Higher keyword score is better
        original_distance = doc.get('distance', 1.0)
        
        # Hybrid score: 70% semantic, 30% keyword
        hybrid_score = (original_distance * 0.7) + ((1 - keyword_score_normalized) * 0.3)
        doc['hybrid_score'] = hybrid_score
        doc['keyword_score'] = keyword_score_normalized
    
    # Sort by hybrid score (lower is better)
    results.sort(key=lambda x: x.get('hybrid_score', x.get('distance', 1.0)))
    
    logger.debug(f"Re-ranked {len(results)} results by hybrid score")
    
    return results[:k]


def detect_hallucination(generated_text: str, retrieved_docs: List[Dict]) -> Dict[str, Any]:
    """
    Day 8 Enhanced: Detect potential hallucinations using semantic similarity + word overlap
    
    Combines two methods:
    1. Word overlap (fast, strict)
    2. Semantic similarity via embeddings (accurate, catches paraphrasing)
    
    Args:
        generated_text: The AI-generated content to verify
        retrieved_docs: List of documents retrieved from RAG (with 'text' field)
        
    Returns:
        {
            "has_hallucination_risk": bool,
            "unsupported_claims": List[str],
            "support_score": float (0-1),
            "total_sentences": int,
            "supported_sentences": int | float
        }
    """
    if not retrieved_docs:
        logger.warning("No RAG context available for hallucination detection")
        return {
            "has_hallucination_risk": True,
            "unsupported_claims": ["No RAG context available"],
            "support_score": 0.0,
            "total_sentences": 0,
            "supported_sentences": 0
        }
    
    # Simple sentence splitting (naive approach - production would use nltk)
    sentences = [s.strip() for s in generated_text.split('.') if s.strip() and len(s.strip()) > 10]
    
    if not sentences:
        return {
            "has_hallucination_risk": False,
            "unsupported_claims": [],
            "support_score": 1.0,
            "total_sentences": 0,
            "supported_sentences": 0
        }
    
    # Combine all retrieved text for comparison
    rag_context = " ".join([doc.get('text', '') for doc in retrieved_docs])
    rag_context_lower = rag_context.lower()
    
    # Get embedding model for semantic similarity
    try:
        model = get_embedding_model()
        
        # Encode sentences and RAG context
        sentence_embeddings = model.encode(sentences, show_progress_bar=False)
        rag_embedding = model.encode([rag_context], show_progress_bar=False)[0]
        
        use_semantic = True
        logger.debug("Using semantic similarity for hallucination detection")
    except Exception as e:
        logger.warning(f"Failed to load embedding model, falling back to word overlap: {e}")
        use_semantic = False
    
    unsupported = []
    supported_count = 0.0
    
    for i, sentence in enumerate(sentences):
        # Method 1: Word overlap (fast baseline)
        words = [
            word.lower() for word in sentence.split() 
            if len(word) >= 3 and word.lower() not in {'this', 'that', 'with', 'from', 'have', 'been', 'were'}
        ]
        
        if not words:
            supported_count += 1.0  # Empty sentence, don't penalize
            continue
        
        word_matches = sum(1 for word in words if word in rag_context_lower)
        word_overlap = word_matches / len(words) if words else 0.0
        
        # Method 2: Semantic similarity (if available)
        if use_semantic:
            similarity = cosine_similarity([sentence_embeddings[i]], [rag_embedding])[0][0]
            
            # Combined scoring: 40% word overlap + 60% semantic similarity
            combined_score = (word_overlap * 0.4) + (similarity * 0.6)
            
            if combined_score >= 0.45:  # High confidence threshold
                supported_count += 1.0
            elif combined_score >= 0.30:  # Partial support
                supported_count += 0.6
            elif combined_score >= 0.20:  # Weak support
                supported_count += 0.3
                unsupported.append(sentence[:100])
            else:
                unsupported.append(sentence[:100])
            
            logger.debug(f"Sentence semantic={similarity:.2f}, word={word_overlap:.2f}, combined={combined_score:.2f}")
        else:
            # Fallback to word overlap only
            if word_overlap >= 0.30:
                supported_count += 1.0
            elif word_overlap >= 0.20:
                supported_count += 0.5
                unsupported.append(sentence[:100])
            else:
                unsupported.append(sentence[:100])
    
    support_score = supported_count / len(sentences) if sentences else 0.0
    
    # Flag as high risk if support score is below 0.5
    has_risk = support_score < 0.5
    
    logger.info(f"Hallucination check: {supported_count:.1f}/{len(sentences)} sentences supported (score: {support_score:.2f}, method: {'semantic+word' if use_semantic else 'word-only'})")
    
    return {
        "has_hallucination_risk": has_risk,
        "unsupported_claims": unsupported[:3],  # Return max 3 examples
        "support_score": support_score,
        "total_sentences": len(sentences),
        "supported_sentences": supported_count
    }
