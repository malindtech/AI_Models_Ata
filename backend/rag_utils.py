# backend/rag_utils.py
"""
RAG (Retrieval-Augmented Generation) Utilities

Helper functions for integrating retrieved context into prompts:
- Context formatting and truncation
- Prompt injection
- Token estimation
- Duplicate filtering
"""

from typing import List, Dict, Any
from loguru import logger


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
