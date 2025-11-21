"""
Knowledge Base Module - Policy and FAQ retrieval using vector search
Loads company policies and provides semantic search capabilities
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Any
from loguru import logger

# Try to import vector DB components
try:
    from backend.vector_store import create_or_get_collection, initialize_chroma_client
    import chromadb
    VECTOR_DB_AVAILABLE = True
except ImportError:
    logger.warning("Vector DB not available for knowledge base")
    VECTOR_DB_AVAILABLE = False


class KnowledgeBase:
    """
    Policy and FAQ knowledge base with semantic search
    Uses ChromaDB for vector similarity search
    """
    
    def __init__(self, policies_file: str = None, chroma_client=None):
        """
        Initialize knowledge base and load policies
        
        Args:
            policies_file: Path to policies CSV file (defaults to data/company/policies.csv in project root)
            chroma_client: Optional ChromaDB client (will create if None)
        """
        # Default to project root /data/company/policies.csv
        if policies_file is None:
            project_root = Path(__file__).parent.parent
            policies_file = project_root / "data" / "company" / "policies.csv"
        
        self.policies_file = Path(policies_file)
        self.policies_df = None
        self.policy_cache = {}  # In-memory cache for frequently accessed policies
        self.chroma_client = chroma_client
        self.collection = None
        
        # Load policies from CSV
        self._load_policies()
        
        # Initialize vector store if available (with error handling)
        if VECTOR_DB_AVAILABLE:
            try:
                self._initialize_vector_store()
            except Exception as e:
                logger.warning(f"⚠️ Vector store initialization failed: {e}")
                logger.info("Falling back to keyword-based policy search")
                self.collection = None
        else:
            logger.warning("⚠️ Vector search unavailable - using keyword-based search")
    
    def _load_policies(self):
        """Load policies from CSV file"""
        if not self.policies_file.exists():
            logger.error(f"Policies file not found: {self.policies_file}")
            self.policies_df = pd.DataFrame()
            return
        
        try:
            self.policies_df = pd.read_csv(self.policies_file)
            logger.info(f"✅ Loaded {len(self.policies_df)} policies from {self.policies_file}")
            
            # Build cache of policies by type
            for _, row in self.policies_df.iterrows():
                policy_type = row.get('policy_type', 'unknown')
                if policy_type not in self.policy_cache:
                    self.policy_cache[policy_type] = []
                self.policy_cache[policy_type].append(row.to_dict())
            
            logger.debug(f"Policy types cached: {list(self.policy_cache.keys())}")
        except Exception as e:
            logger.error(f"Failed to load policies: {e}")
            self.policies_df = pd.DataFrame()
    
    def _initialize_vector_store(self):
        """Initialize ChromaDB collection for policies"""
        try:
            if self.chroma_client is None:
                self.chroma_client = initialize_chroma_client()
            
            # Create/get policies collection
            self.collection = create_or_get_collection(
                collection_name="policies",
                client=self.chroma_client
            )
            
            # Check if collection is empty and needs population
            count = self.collection.count()
            
            if count == 0 and not self.policies_df.empty:
                logger.info("Populating policies collection...")
                self._populate_vector_store()
            else:
                logger.info(f"✅ Policies collection ready ({count} documents)")
        
        except Exception as e:
            logger.error(f"Failed to initialize vector store for policies: {e}")
            self.collection = None
    
    def _populate_vector_store(self):
        """Populate vector store with policy documents"""
        if self.collection is None or self.policies_df.empty:
            return
        
        try:
            documents = []
            metadatas = []
            ids = []
            
            for idx, row in self.policies_df.iterrows():
                # Combine title and content for better search
                doc_text = f"{row['title']}. {row['content']}"
                documents.append(doc_text)
                
                metadatas.append({
                    "policy_id": str(row['policy_id']),
                    "policy_type": str(row['policy_type']),
                    "title": str(row['title'])
                })
                
                ids.append(f"policy_{idx}")
            
            # Add to collection
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"✅ Added {len(documents)} policies to vector store")
        
        except Exception as e:
            logger.error(f"Failed to populate vector store: {e}")
    
    def get_relevant_policies(
        self, 
        query: str, 
        k: int = 3,
        policy_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant policies using semantic search
        
        Args:
            query: Search query (customer message or intent)
            k: Number of policies to retrieve
            policy_type: Optional filter by policy type
        
        Returns:
            List of policy dicts with content and metadata
        """
        if self.policies_df.empty:
            logger.warning("No policies loaded")
            return []
        
        # Try vector search first
        if self.collection is not None:
            return self._vector_search(query, k, policy_type)
        
        # Fallback to keyword search
        return self._keyword_search(query, k, policy_type)
    
    def _vector_search(
        self, 
        query: str, 
        k: int,
        policy_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Semantic search using vector similarity"""
        try:
            # Build filter if policy_type specified
            where_filter = None
            if policy_type:
                where_filter = {"policy_type": policy_type}
            
            # Query collection
            results = self.collection.query(
                query_texts=[query],
                n_results=k,
                where=where_filter
            )
            
            policies = []
            
            if results and results.get('metadatas'):
                for i, metadata in enumerate(results['metadatas'][0]):
                    # Get full policy from dataframe
                    policy_id = metadata.get('policy_id')
                    policy_row = self.policies_df[
                        self.policies_df['policy_id'] == policy_id
                    ]
                    
                    if not policy_row.empty:
                        policy = policy_row.iloc[0].to_dict()
                        policy['relevance_score'] = 1.0 - results['distances'][0][i]  # Convert distance to similarity
                        policies.append(policy)
            
            logger.info(f"✅ Vector search found {len(policies)} relevant policies")
            return policies
        
        except Exception as e:
            logger.error(f"Vector search failed: {e}, falling back to keyword search")
            return self._keyword_search(query, k, policy_type)
    
    def _keyword_search(
        self, 
        query: str, 
        k: int,
        policy_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fallback keyword-based search"""
        query_lower = query.lower()
        df = self.policies_df.copy()
        
        # Filter by type if specified
        if policy_type:
            df = df[df['policy_type'] == policy_type]
        
        # Score policies by keyword matches
        scores = []
        for _, row in df.iterrows():
            content = f"{row['title']} {row['content']}".lower()
            
            # Count keyword matches
            score = sum(1 for word in query_lower.split() if word in content)
            scores.append(score)
        
        df['score'] = scores
        
        # Sort by score and return top k
        top_policies = df.nlargest(k, 'score')
        policies = []
        
        for _, row in top_policies.iterrows():
            if row['score'] > 0:  # Only include if at least one keyword matched
                policy = row.to_dict()
                policy['relevance_score'] = row['score'] / 10.0  # Normalize
                policies.append(policy)
        
        logger.info(f"✅ Keyword search found {len(policies)} relevant policies")
        return policies
    
    def get_policy_by_type(self, policy_type: str) -> List[Dict[str, Any]]:
        """
        Get all policies of a specific type (cached)
        
        Args:
            policy_type: Policy type (shipping, returns, warranty, etc.)
        
        Returns:
            List of matching policy dicts
        """
        return self.policy_cache.get(policy_type, [])
    
    def format_policy_context(self, policies: List[Dict[str, Any]]) -> str:
        """
        Format policies into readable context string
        
        Args:
            policies: List of policy dicts
        
        Returns:
            Formatted policy context
        """
        if not policies:
            return "No relevant policies found"
        
        context_parts = ["RELEVANT COMPANY POLICIES:"]
        
        for i, policy in enumerate(policies, 1):
            title = policy.get('title', 'Unknown Policy')
            content = policy.get('content', '')
            policy_type = policy.get('policy_type', 'general')
            
            context_parts.append(f"\n{i}. {title} ({policy_type.title()})")
            context_parts.append(f"   {content}")
        
        return "\n".join(context_parts)
    
    def get_policy_summary(self) -> Dict[str, int]:
        """Get summary of available policies by type"""
        summary = {}
        for policy_type, policies in self.policy_cache.items():
            summary[policy_type] = len(policies)
        return summary


# Global singleton instance
_knowledge_base_instance: Optional[KnowledgeBase] = None


def get_knowledge_base(chroma_client=None) -> KnowledgeBase:
    """
    Get or create global KnowledgeBase instance (singleton pattern)
    
    Args:
        chroma_client: Optional ChromaDB client
    
    Returns:
        KnowledgeBase instance
    """
    global _knowledge_base_instance
    
    if _knowledge_base_instance is None:
        try:
            _knowledge_base_instance = KnowledgeBase(chroma_client=chroma_client)
            logger.info("✅ Global KnowledgeBase instance created")
        except Exception as e:
            logger.error(f"Failed to create KnowledgeBase: {e}")
            raise
    
    return _knowledge_base_instance


def reload_knowledge_base(chroma_client=None):
    """Force reload of KnowledgeBase (useful for testing or data updates)"""
    global _knowledge_base_instance
    _knowledge_base_instance = None
    return get_knowledge_base(chroma_client=chroma_client)
