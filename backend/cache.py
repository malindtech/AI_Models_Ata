"""
Day 9: Redis Caching Layer
Provides high-performance caching for RAG retrieval, intent classification, and data loading
Uses Redis DB 1 (separate from Celery which uses DB 0)
"""

import redis
import json
import hashlib
import os
from functools import wraps
from typing import Any, Callable, Optional, Union
from loguru import logger
from datetime import timedelta


# Redis configuration (using separate DB from Celery)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_CACHE_DB = int(os.getenv("REDIS_CACHE_DB", "1"))  # DB 1 for caching (Celery uses DB 0)
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Cache TTL defaults (in seconds)
DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", "3600"))  # 1 hour
RAG_RETRIEVAL_TTL = int(os.getenv("CACHE_RAG_TTL", "3600"))  # 1 hour
INTENT_CLASSIFICATION_TTL = int(os.getenv("CACHE_INTENT_TTL", "1800"))  # 30 minutes
DATA_LOADER_TTL = int(os.getenv("CACHE_DATA_TTL", "7200"))  # 2 hours
QUERY_EXPANSION_TTL = int(os.getenv("CACHE_EXPANSION_TTL", "3600"))  # 1 hour


class RedisCache:
    """
    Redis caching client with connection pooling and error handling
    
    Features:
    - Automatic serialization/deserialization
    - TTL management
    - Cache statistics tracking
    - Graceful degradation on Redis failures
    """
    
    def __init__(self, db: int = REDIS_CACHE_DB):
        self.db = db
        self._client = None
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
    
    @property
    def client(self) -> Optional[redis.Redis]:
        """Lazy-load Redis client with connection pooling"""
        if self._client is None:
            try:
                self._client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=self.db,
                    password=REDIS_PASSWORD,
                    decode_responses=False,  # Handle bytes for JSON
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                # Test connection
                self._client.ping()
                logger.info(f"✅ Redis cache connected: {REDIS_HOST}:{REDIS_PORT} DB {self.db}")
            except Exception as e:
                logger.error(f"❌ Redis connection failed: {e}")
                self._client = None
        
        return self._client
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Returns:
            Cached value if exists, None otherwise
        """
        if not self.client:
            return None
        
        try:
            value = self.client.get(key)
            if value:
                self._stats["hits"] += 1
                # Deserialize JSON
                return json.loads(value)
            else:
                self._stats["misses"] += 1
                return None
        except Exception as e:
            logger.warning(f"Cache get error for key '{key}': {e}")
            self._stats["errors"] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        """
        Set value in cache with TTL
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds
        
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            # Serialize to JSON
            serialized = json.dumps(value, default=str)
            self.client.setex(key, ttl, serialized)
            self._stats["sets"] += 1
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key '{key}': {e}")
            self._stats["errors"] += 1
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.client:
            return False
        
        try:
            self.client.delete(key)
            self._stats["deletes"] += 1
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key '{key}': {e}")
            self._stats["errors"] += 1
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern
        
        Args:
            pattern: Redis key pattern (e.g., "rag:*")
        
        Returns:
            Number of keys deleted
        """
        if not self.client:
            return 0
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                deleted = self.client.delete(*keys)
                self._stats["deletes"] += deleted
                return deleted
            return 0
        except Exception as e:
            logger.warning(f"Cache delete pattern error for '{pattern}': {e}")
            self._stats["errors"] += 1
            return 0
    
    def clear_all(self) -> bool:
        """Clear entire cache database (use with caution!)"""
        if not self.client:
            return False
        
        try:
            self.client.flushdb()
            logger.warning(f"🗑️ Cleared entire cache DB {self.db}")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            self._stats["errors"] += 1
            return False
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0.0
        
        stats = {
            **self._stats,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2)
        }
        
        # Add Redis info if available
        if self.client:
            try:
                info = self.client.info("stats")
                stats["redis_keyspace_hits"] = info.get("keyspace_hits", 0)
                stats["redis_keyspace_misses"] = info.get("keyspace_misses", 0)
            except:
                pass
        
        return stats
    
    def reset_stats(self):
        """Reset statistics counters"""
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }


# Global cache instance
_cache = RedisCache()


def get_cache() -> RedisCache:
    """Get global cache instance"""
    return _cache


def generate_cache_key(*args, prefix: str = "cache", **kwargs) -> str:
    """
    Generate deterministic cache key from arguments
    
    Args:
        *args: Positional arguments
        prefix: Key prefix for namespacing
        **kwargs: Keyword arguments
    
    Returns:
        Cache key string
    """
    # Combine all arguments into a string
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_string = ":".join(key_parts)
    
    # Hash to keep keys reasonably sized
    key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]
    
    return f"{prefix}:{key_hash}"


# ==== Caching Decorators ====

def cache_rag_retrieval(ttl: int = RAG_RETRIEVAL_TTL):
    """
    Decorator for caching RAG retrieval results
    
    Usage:
        @cache_rag_retrieval(ttl=3600)
        def retrieve_similar(collection, query, k=5):
            # ... retrieval logic ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract key parameters
            if len(args) >= 2:
                collection = args[0]
                query = args[1]
                k = args[2] if len(args) >= 3 else kwargs.get('k', 5)
            else:
                collection = kwargs.get('collection_name') or kwargs.get('collection')
                query = kwargs.get('query')
                k = kwargs.get('k', 5)
            
            # Generate cache key
            cache_key = f"rag:{collection}:{hashlib.md5(query.encode()).hexdigest()[:16]}:k{k}"
            
            # Try cache first
            cached = _cache.get(cache_key)
            if cached is not None:
                logger.debug(f"✅ Cache HIT: RAG retrieval for '{query[:30]}...'")
                return cached
            
            # Cache miss - call original function
            logger.debug(f"❌ Cache MISS: RAG retrieval for '{query[:30]}...'")
            result = func(*args, **kwargs)
            
            # Store in cache
            _cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


def cache_intent_classification(ttl: int = INTENT_CLASSIFICATION_TTL):
    """
    Decorator for caching intent classification results
    
    Usage:
        @cache_intent_classification(ttl=1800)
        def classify_intent(message):
            # ... classification logic ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(message: str, *args, **kwargs):
            # Generate cache key from message hash
            cache_key = f"intent:{hashlib.md5(message.encode()).hexdigest()[:16]}"
            
            # Try cache first
            cached = _cache.get(cache_key)
            if cached is not None:
                logger.debug(f"✅ Cache HIT: Intent classification")
                return cached
            
            # Cache miss
            logger.debug(f"❌ Cache MISS: Intent classification")
            result = func(message, *args, **kwargs)
            
            # Store in cache
            _cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


def cache_query_expansion(ttl: int = QUERY_EXPANSION_TTL):
    """
    Decorator for caching query expansion results
    
    Usage:
        @cache_query_expansion(ttl=3600)
        def expand_query(query, max_expansions=3):
            # ... expansion logic ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(query: str, *args, **kwargs):
            max_expansions = kwargs.get('max_expansions', 3)
            include_synonyms = kwargs.get('include_synonyms', True)
            include_related = kwargs.get('include_related', True)
            
            # Generate cache key
            cache_key = f"expansion:{hashlib.md5(query.encode()).hexdigest()[:16]}:{max_expansions}:{include_synonyms}:{include_related}"
            
            # Try cache first
            cached = _cache.get(cache_key)
            if cached is not None:
                logger.debug(f"✅ Cache HIT: Query expansion")
                return cached
            
            # Cache miss
            logger.debug(f"❌ Cache MISS: Query expansion")
            result = func(query, *args, **kwargs)
            
            # Store in cache
            _cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


def cache_data_loader(ttl: int = DATA_LOADER_TTL):
    """
    Decorator for caching data loader results (customers, orders, etc.)
    
    Usage:
        @cache_data_loader(ttl=7200)
        def load_customers():
            # ... loading logic ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name
            func_name = func.__name__
            cache_key = f"data:{func_name}"
            
            # Try cache first
            cached = _cache.get(cache_key)
            if cached is not None:
                logger.debug(f"✅ Cache HIT: {func_name}")
                # Convert back to DataFrame if needed
                if isinstance(cached, dict) and 'data' in cached:
                    import pandas as pd
                    return pd.DataFrame(cached['data'])
                return cached
            
            # Cache miss
            logger.debug(f"❌ Cache MISS: {func_name}")
            result = func(*args, **kwargs)
            
            # Store in cache (convert DataFrame to dict for JSON serialization)
            if hasattr(result, 'to_dict'):
                cached_value = {'data': result.to_dict('records')}
            else:
                cached_value = result
            
            _cache.set(cache_key, cached_value, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


# ==== Distributed Rate Limiting ====

class RedisRateLimiter:
    """
    Redis-backed distributed rate limiter
    Replaces in-memory rate limiting with persistent, distributed solution
    """
    
    def __init__(self, cache: RedisCache = None):
        self.cache = cache or _cache
    
    def check_limit(
        self, 
        identifier: str, 
        max_requests: int, 
        window_seconds: int,
        block_duration: int = 300
    ) -> tuple[bool, dict]:
        """
        Check if request is within rate limit
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
            block_duration: Block duration in seconds if limit exceeded
        
        Returns:
            (allowed: bool, info: dict)
        """
        if not self.cache.client:
            # Fallback: allow if Redis unavailable
            logger.warning("Redis unavailable, rate limiting disabled")
            return True, {"remaining": max_requests, "retry_after": 0}
        
        now = int(os.times().system)  # Current timestamp
        window_key = f"ratelimit:{identifier}:window"
        count_key = f"ratelimit:{identifier}:count"
        block_key = f"ratelimit:{identifier}:blocked"
        
        try:
            # Check if blocked
            blocked_until = self.cache.get(block_key)
            if blocked_until and now < blocked_until:
                retry_after = int(blocked_until - now)
                return False, {
                    "remaining": 0,
                    "retry_after": retry_after,
                    "reset_at": blocked_until
                }
            
            # Get current count and window start
            count = self.cache.get(count_key) or 0
            window_start = self.cache.get(window_key) or now
            
            # Check if window expired
            if now - window_start > window_seconds:
                # Reset window
                self.cache.set(window_key, now, ttl=window_seconds)
                self.cache.set(count_key, 1, ttl=window_seconds)
                return True, {
                    "remaining": max_requests - 1,
                    "retry_after": 0,
                    "reset_at": now + window_seconds
                }
            
            # Check if limit exceeded
            if count >= max_requests:
                # Block the identifier
                blocked_until = now + block_duration
                self.cache.set(block_key, blocked_until, ttl=block_duration)
                logger.warning(f"Rate limit exceeded for {identifier}, blocked for {block_duration}s")
                return False, {
                    "remaining": 0,
                    "retry_after": block_duration,
                    "reset_at": blocked_until
                }
            
            # Increment counter
            new_count = count + 1
            self.cache.set(count_key, new_count, ttl=window_seconds)
            
            remaining = max_requests - new_count
            reset_at = window_start + window_seconds
            
            return True, {
                "remaining": remaining,
                "retry_after": 0,
                "reset_at": reset_at
            }
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Fallback: allow on error
            return True, {"remaining": max_requests, "retry_after": 0}
    
    def reset(self, identifier: str):
        """Reset rate limit for identifier"""
        pattern = f"ratelimit:{identifier}:*"
        deleted = self.cache.delete_pattern(pattern)
        logger.info(f"Reset rate limit for {identifier} ({deleted} keys)")


# Global rate limiter instance
_rate_limiter = RedisRateLimiter()


def get_rate_limiter() -> RedisRateLimiter:
    """Get global rate limiter instance"""
    return _rate_limiter


if __name__ == "__main__":
    # Test cache functionality
    print("\n=== Testing Redis Cache ===\n")
    
    cache = get_cache()
    
    # Test basic operations
    print("1. Testing basic set/get...")
    cache.set("test_key", {"message": "Hello, Redis!"}, ttl=60)
    result = cache.get("test_key")
    print(f"   Retrieved: {result}")
    
    # Test cache decorator
    print("\n2. Testing cache decorator...")
    
    @cache_rag_retrieval(ttl=60)
    def mock_retrieval(collection, query, k=5):
        print(f"   [SLOW OPERATION] Retrieving from {collection}...")
        return [{"id": "1", "text": "cached result"}]
    
    # First call (miss)
    print("   First call (should be MISS):")
    result1 = mock_retrieval("test_collection", "test query", k=5)
    
    # Second call (hit)
    print("   Second call (should be HIT):")
    result2 = mock_retrieval("test_collection", "test query", k=5)
    
    # Print stats
    print("\n3. Cache statistics:")
    stats = cache.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Test rate limiter
    print("\n4. Testing rate limiter...")
    limiter = get_rate_limiter()
    
    for i in range(3):
        allowed, info = limiter.check_limit("test_user", max_requests=2, window_seconds=60)
        print(f"   Request {i+1}: Allowed={allowed}, Remaining={info['remaining']}")
    
    print("\n✅ Cache tests complete!\n")
