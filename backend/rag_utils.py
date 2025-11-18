# backend/rag_utils.py
"""
RAG (Retrieval-Augmented Generation) Utilities

Helper functions for integrating retrieved context into prompts:
- Query expansion for better retrieval
- Context formatting and truncation
- Prompt injection with personalization
- Token estimation
- Duplicate filtering
"""

from typing import List, Dict, Any
import re
from loguru import logger


def expand_query(query: str, num_variations: int = 3) -> List[str]:
    """
    Generate query variations for improved retrieval (query expansion)
    
    Strategies:
    1. Original query
    2. Generalized query (remove specific details)
    3. Synonym/related terms query
    4. Simplified/condensed query
    
    Args:
        query: Original user query
        num_variations: Number of variations to generate (including original)
        
    Returns:
        List of query variations for retrieval
        
    Example:
        >>> expand_query("My laptop won't turn on")
        [
            "My laptop won't turn on",  # Original
            "laptop power issue",        # Generalized
            "device won't start"         # Synonym variation
        ]
    """
    variations = [query]  # Always include original
    
    if num_variations <= 1:
        return variations
    
    # Strategy 1: Generalized (remove specific product names/brands)
    generalized = query
    # Remove brand names and specific products
    generalized = re.sub(r'\b(iPhone|Samsung|Dell|HP|Apple|Microsoft|Windows|MacOS)\b', '', generalized, flags=re.IGNORECASE)
    generalized = re.sub(r'\s+', ' ', generalized).strip()
    if generalized and generalized != query and len(variations) < num_variations:
        variations.append(generalized)
    
    # Strategy 2: Simplified (focus on main noun)
    # Extract key problem/topic words
    problem_keywords = {
        "won't": "not working",
        "can't": "unable",
        "doesn't": "not functioning",
        "broken": "damaged",
        "crash": "error",
        "freeze": "hang",
        "slow": "performance issue",
        "loud": "noise",
        "hot": "temperature issue"
    }
    
    simplified = query.lower()
    for issue, replacement in problem_keywords.items():
        simplified = simplified.replace(issue, replacement)
    
    simplified = simplified.strip()
    if simplified and simplified != query.lower() and len(variations) < num_variations:
        variations.append(simplified)
    
    # Strategy 3: Extract core question (if it's a question)
    if '?' in query:
        # For questions, focus on the main question
        question_words = r'\b(what|how|why|when|where|who|which|can|could|would|should|is|are|has|have|does|do)\b'
        core = re.sub(question_words, '', query, flags=re.IGNORECASE).strip()
        core = re.sub(r'\s+', ' ', core).strip()
        if core and len(variations) < num_variations:
            variations.append(core)
    
    logger.debug(f"Generated {len(variations)} query variations from: {query}")
    return variations[:num_variations]


def retrieve_with_expanded_queries(
    collection_name: str,
    query: str,
    client,
    k: int = 5,
    num_query_variations: int = 2
) -> List[Dict[str, Any]]:
    """
    Retrieve documents using expanded queries and deduplicate results
    
    This function:
    1. Expands the query into multiple variations
    2. Retrieves from each variation
    3. Deduplicates and ranks by relevance
    4. Returns top-k results
    
    Args:
        collection_name: ChromaDB collection to search
        query: Original user query
        client: ChromaDB client
        k: Number of top results to return
        num_query_variations: Number of query variations to try (1-3)
        
    Returns:
        List of deduplicated retrieved documents, ranked by relevance
    """
    from backend.vector_store import retrieve_similar
    
    # Generate query variations
    query_variations = expand_query(query, num_query_variations)
    logger.info(f"Searching with {len(query_variations)} query variations")
    
    # Collect results from all variations
    all_results = []
    seen_ids = set()
    
    for variation in query_variations:
        try:
            results = retrieve_similar(collection_name, variation, k=k, client=client)
            
            # Track unique documents (by ID)
            for doc in results:
                doc_id = doc.get('id', '')
                if doc_id not in seen_ids:
                    all_results.append(doc)
                    seen_ids.add(doc_id)
                    
            logger.debug(f"Retrieved {len(results)} results for variation: {variation}")
        except Exception as e:
            logger.warning(f"Retrieval failed for variation '{variation}': {e}")
            continue
    
    # Sort by distance (relevance) and return top-k
    ranked_results = sorted(all_results, key=lambda x: x.get('distance', 1.0))[:k]
    logger.info(f"Query expansion: {len(query_variations)} variations -> {len(ranked_results)} unique results")
    
    return ranked_results



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


def inject_rag_context(base_prompt: str, context: str, customer_name: str = None) -> str:
    """
    Inject retrieved context into base prompt with optional personalization
    
    Strategy: Add context section after system instructions but before user query
    
    Args:
        base_prompt: Original prompt template
        context: Formatted retrieved context
        customer_name: Optional customer name for personalization
        
    Returns:
        Enhanced prompt with context and personalization
        
    Template:
        {system_instructions}
        
        Relevant Context from Similar Cases:
        {context}
        
        {user_query}
        
    Personalization:
        If customer_name is provided, replaces {customer_name} placeholders
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
    
    # Add personalization if customer name provided
    if customer_name:
        enhanced_prompt = enhanced_prompt.replace("{customer_name}", customer_name)
        logger.debug(f"Personalized prompt with customer name: {customer_name}")
    
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


def personalize_response(response: str, customer_name: str = None, customer_id: str = None) -> str:
    """
    Add personalization to generated response
    
    Replaces placeholders:
    - {customer_name}: Customer's name
    - {customer_id}: Customer's unique ID
    - {first_name}: First name extracted from customer_name
    
    Args:
        response: Original generated response
        customer_name: Full customer name or None
        customer_id: Customer ID or None
        
    Returns:
        Personalized response with placeholders replaced
        
    Example:
        >>> personalize_response(
        ...     "Hi {customer_name}, thank you for contacting us!",
        ...     customer_name="John Smith"
        ... )
        "Hi John Smith, thank you for contacting us!"
    """
    personalized = response
    
    if customer_name:
        personalized = personalized.replace("{customer_name}", customer_name)
        
        # Extract first name
        first_name = customer_name.split()[0] if customer_name else ""
        personalized = personalized.replace("{first_name}", first_name)
        
        logger.debug(f"Personalized response with customer name: {customer_name}")
    
    if customer_id:
        personalized = personalized.replace("{customer_id}", str(customer_id))
        logger.debug(f"Personalized response with customer ID: {customer_id}")
    
    return personalized

