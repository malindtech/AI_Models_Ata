# backend/vector_store.py
"""
Vector Store Module - ChromaDB Integration for Day 5

Provides centralized operations for:
- ChromaDB initialization and persistence
- Document embedding using all-MiniLM-L6-v2
- Semantic search and retrieval
- Cross-collection search
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    import chromadb

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError as e:
    logger.warning(f"ChromaDB not installed: {e}")
    logger.warning("Install with: pip install chromadb sentence-transformers")
    CHROMADB_AVAILABLE = False
    chromadb = None  # Set to None for type hints


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
CHROMA_DB_PATH = PROJECT_ROOT / "data" / "chroma_db"

# Global client cache
_chroma_client = None
_embedding_function = None


def initialize_chroma_client():
    """
    Initialize ChromaDB client with persistent storage
    
    Returns:
        chromadb.Client: Persistent ChromaDB client
        
    Raises:
        ImportError: If chromadb is not installed
        Exception: If initialization fails
    """
    global _chroma_client
    
    if not CHROMADB_AVAILABLE:
        raise ImportError("ChromaDB not available. Install: pip install chromadb sentence-transformers")
    
    # Return cached client if available
    if _chroma_client is not None:
        return _chroma_client
    
    try:
        # Ensure directory exists
        CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
        
        # Create persistent client
        _chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_DB_PATH),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        logger.info(f"ChromaDB initialized at: {CHROMA_DB_PATH}")
        return _chroma_client
        
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB: {e}")
        raise


def get_embedding_function():
    """
    Get or create the embedding function (all-MiniLM-L6-v2)
    
    Returns:
        EmbeddingFunction: Sentence transformer embedding function
    """
    global _embedding_function
    
    if _embedding_function is not None:
        return _embedding_function
    
    try:
        # Try ChromaDB's built-in function first
        try:
            _embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            logger.info("Loaded embedding model: all-MiniLM-L6-v2 (ChromaDB)")
            return _embedding_function
        except Exception as chroma_error:
            logger.warning(f"ChromaDB embedding function failed: {chroma_error}, trying direct import")
            
            # Fallback: Direct sentence-transformers import
            from sentence_transformers import SentenceTransformer
            import chromadb.utils.embedding_functions as ef
            
            # Create custom embedding function
            class DirectSentenceTransformerEF(ef.EmbeddingFunction):
                def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
                    self.model = SentenceTransformer(model_name)
                    
                def __call__(self, texts):
                    embeddings = self.model.encode(texts, convert_to_numpy=True)
                    return embeddings.tolist()
            
            _embedding_function = DirectSentenceTransformerEF()
            logger.info("Loaded embedding model: all-MiniLM-L6-v2 (direct)")
            return _embedding_function
        
    except Exception as e:
        logger.error(f"Failed to load embedding function: {e}")
        raise


def create_or_get_collection(
    collection_name: str,
    client = None
):
    """
    Create or get existing collection
    
    Args:
        collection_name: Name of the collection
        client: ChromaDB client (creates new if None)
        
    Returns:
        chromadb.Collection: Collection object
    """
    if client is None:
        client = initialize_chroma_client()
    
    embedding_fn = get_embedding_function()
    
    try:
        # Try to get existing collection
        collection = client.get_collection(
            name=collection_name,
            embedding_function=embedding_fn
        )
        logger.debug(f"Retrieved existing collection: {collection_name}")
        
    except Exception:
        # Create new collection if doesn't exist
        collection = client.create_collection(
            name=collection_name,
            embedding_function=embedding_fn,
            metadata={"description": f"Collection for {collection_name} dataset"}
        )
        logger.info(f"Created new collection: {collection_name}")
    
    return collection


def add_documents(
    collection,
    documents: List[Dict[str, Any]],
    batch_size: int = 50
) -> bool:
    """
    Add documents to collection in batches
    
    Args:
        collection: ChromaDB collection
        documents: List of dicts with 'id', 'text', 'metadata' keys
        batch_size: Number of documents per batch
        
    Returns:
        bool: True if successful
        
    Expected document format:
        {
            'id': 'unique_id',
            'text': 'document text content',
            'metadata': {'key': 'value', ...}
        }
    """
    try:
        # Process in batches
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            ids = [doc['id'] for doc in batch]
            texts = [doc['text'] for doc in batch]
            metadatas = [doc.get('metadata', {}) for doc in batch]
            
            collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
        
        logger.info(f"Added {len(documents)} documents to collection '{collection.name}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add documents to {collection.name}: {e}")
        raise


def retrieve_similar(
    collection_name: str,
    query: str,
    k: int = 5,
    client = None
) -> List[Dict[str, Any]]:
    """
    Retrieve top-k similar documents from a collection
    
    Args:
        collection_name: Name of the collection to search
        query: Search query text
        k: Number of results to return
        client: ChromaDB client (creates new if None)
        
    Returns:
        List of dicts with keys: id, text, metadata, distance
        
    Raises:
        ValueError: If collection doesn't exist
    """
    if client is None:
        client = initialize_chroma_client()
    
    # Validate collection_name is a string
    if not isinstance(collection_name, str):
        logger.error(f"collection_name must be string, got {type(collection_name)}")
        raise TypeError(f"collection_name must be string, got {type(collection_name)}")
    
    try:
        collection = create_or_get_collection(collection_name, client)
        
        # Query collection
        results = collection.query(
            query_texts=[query],
            n_results=k
        )
        
        # Format results
        formatted_results = []
        if results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i] if results['metadatas'][0] else {},
                    'distance': results['distances'][0][i] if results['distances'] else 0.0
                })
        
        logger.debug(f"Retrieved {len(formatted_results)} documents from '{collection_name}'")
        return formatted_results
        
    except Exception as e:
        logger.error(f"Failed to retrieve from {collection_name}: {e}")
        raise ValueError(f"Collection '{collection_name}' not found or query failed: {e}")


def retrieve_cross_collection(
    query: str,
    k: int = 3,
    collections: Optional[List[str]] = None,
    client = None
) -> List[Dict[str, Any]]:
    """
    Search across multiple collections and return unified results
    
    Args:
        query: Search query text
        k: Number of results per collection
        collections: List of collection names (default: all available)
        client: ChromaDB client (creates new if None)
        
    Returns:
        List of dicts sorted by distance (most relevant first)
    """
    if client is None:
        client = initialize_chroma_client()
    
    # Default to all known collections
    if collections is None:
        collections = ['blogs', 'products', 'support', 'social', 'reviews']
    
    all_results = []
    
    for collection_name in collections:
        try:
            results = retrieve_similar(collection_name, query, k, client)
            # Add collection name to metadata
            for result in results:
                result['metadata']['_collection'] = collection_name
            all_results.extend(results)
        except Exception as e:
            logger.warning(f"Skipping collection {collection_name}: {e}")
            continue
    
    # Sort by distance (lower is better)
    all_results.sort(key=lambda x: x['distance'])
    
    logger.debug(f"Cross-collection search returned {len(all_results)} total results")
    return all_results


def get_collection_stats(client = None) -> Dict[str, Any]:
    """
    Get statistics about all collections
    
    Returns:
        Dict with collection names and document counts
    """
    if client is None:
        client = initialize_chroma_client()
    
    try:
        collections = client.list_collections()
        stats = {}
        
        for collection in collections:
            col_obj = client.get_collection(collection.name)
            count = col_obj.count()
            stats[collection.name] = count
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get collection stats: {e}")
        return {}


def reset_database(client = None) -> bool:
    """
    Reset the entire database (USE WITH CAUTION!)
    
    Returns:
        bool: True if successful
    """
    if client is None:
        client = initialize_chroma_client()
    
    try:
        client.reset()
        logger.warning("Database reset complete - all collections deleted")
        return True
    except Exception as e:
        logger.error(f"Failed to reset database: {e}")
        return False
