import redis
import json
import pickle
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime
from models.data_models import QueryContext, AgentResponse
import pandas as pd

class RedisCacheAgent:
    """
    Agent responsible for caching and retrieving previous queries using Redis.
    Stores complete query context including SQL query, results, and LLM responses.
    Falls back to joblib if Redis is unavailable.
    """
    
    def __init__(self, 
                 redis_host: str = "localhost",
                 redis_port: int = 6379,
                 redis_db: int = 0,
                 redis_password: Optional[str] = None,
                 ttl_seconds: int = 86400,  # 24 hours default
                 use_fallback: bool = True,
                 cache_dir: str = "cache"):
        """
        Initialize the Redis Cache Agent.
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            redis_password: Redis password (if required)
            ttl_seconds: Time-to-live for cache entries in seconds
            use_fallback: Use joblib fallback if Redis unavailable
            cache_dir: Directory for joblib fallback cache
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.redis_password = redis_password
        self.ttl_seconds = ttl_seconds
        self.use_fallback = use_fallback
        self.redis_client = None
        self.redis_available = False
        
        # Fallback cache (joblib)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.fallback_cache = {}
        
        # Try to connect to Redis
        self._connect_redis()
        
        # Load fallback cache if needed
        if not self.redis_available and self.use_fallback:
            self._load_fallback_cache()
    
    def _connect_redis(self):
        """Establish connection to Redis server."""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_password,
                decode_responses=False,  # We'll handle encoding ourselves
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # Test connection
            self.redis_client.ping()
            self.redis_available = True
            print(f"✅ Connected to Redis at {self.redis_host}:{self.redis_port}")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            self.redis_available = False
            print(f"⚠️ Redis connection failed: {str(e)}")
            if self.use_fallback:
                print("📦 Falling back to joblib cache")
            else:
                print("❌ Cache disabled (no fallback)")
    
    def process(self, context: QueryContext) -> AgentResponse:
        """Process the query context to check for cached queries."""
        try:
            # Look for a cached query (global, not user-specific)
            cached_data = self.get_cached_entry(context.user_question)
            
            if cached_data:
                return AgentResponse(
                    success=True,
                    message="Query found in cache",
                    data={
                        "cache_hit": True,
                        "cached_data": cached_data
                    }
                )
            else:
                return AgentResponse(
                    success=True,
                    message="Query not found in cache",
                    data={
                        "cache_hit": False
                    }
                )
                
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Error in query cache: {str(e)}"
            )
    
    def cache_query(self, context: QueryContext):
        """
        Cache a successful query with complete response data.
        
        Args:
            context: The query context containing all query information
        """
        if not context.sql_query:
            return
        
        # Debug: Show user_id and table_name
        print(f"[Cache Write] user_id={context.user_id}, table_name={context.table_name}")
        print(f"[Cache Write] query={context.user_question[:50]}...")
        
        # Prepare cache entry with complete data
        cache_entry = {
            "sql_query": context.sql_query,
            "formatted_response": context.formatted_response,
            "user_id": context.user_id,
            "timestamp": datetime.now().isoformat(),
            "db_name": context.db_name,
            "table_name": context.table_name
        }
        
        # Optionally include query results (can be large)
        if context.query_results is not None and not context.query_results.empty:
            # Convert DataFrame to dict for JSON serialization
            cache_entry["query_results"] = context.query_results.to_dict('records')
            cache_entry["query_results_columns"] = list(context.query_results.columns)
        
        # Create cache key
        cache_key = self._generate_cache_key(context.user_question, context.user_id)
        
        # Try Redis first
        if self.redis_available:
            try:
                # Serialize using pickle for complex objects
                serialized_data = pickle.dumps(cache_entry)
                self.redis_client.setex(
                    cache_key,
                    self.ttl_seconds,
                    serialized_data
                )
                print(f"✅ Cached query in Redis with TTL={self.ttl_seconds}s")
                return
            except Exception as e:
                print(f"⚠️ Redis cache write failed: {str(e)}")
                if not self.use_fallback:
                    return
        
        # Fallback to joblib
        if self.use_fallback:
            self.fallback_cache[cache_key] = cache_entry
            self._save_fallback_cache()
            print(f"📦 Cached query in joblib fallback")
    
    def get_cached_entry(self, query_text: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a cached entry for a given natural language query.
        Global cache - not user-specific.
        
        Args:
            query_text: The natural language query
            
        Returns:
            The cached entry dictionary or None if not found
        """
        # Debug: Show what we're looking for
        print(f"[Cache Read] Looking for query={query_text[:50]}...")
        
        cache_key = self._generate_cache_key(query_text)
        print(f"[Cache Read] Generated key: {cache_key}")
        
        # Try Redis first
        if self.redis_available:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    entry = pickle.loads(cached_data)
                    print(f"✅ Cache hit from Redis")
                    return entry
            except Exception as e:
                print(f"⚠️ Redis cache read failed: {str(e)}")
        
        # Fallback to joblib
        if self.use_fallback:
            if cache_key in self.fallback_cache:
                print(f"📦 Cache hit from joblib fallback")
                return self.fallback_cache[cache_key]
        
        return None
    
    def clear_cache(self):
        """
        Clear all cache entries (global cache).
        """
        # Clear all cache
        pattern = "cache:*"
        
        # Clear from Redis
        if self.redis_available:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                    print(f"✅ Cleared {len(keys)} entries from Redis")
            except Exception as e:
                print(f"⚠️ Redis cache clear failed: {str(e)}")
        
        # Clear from fallback
        if self.use_fallback:
            self.fallback_cache.clear()
            self._save_fallback_cache()
            print(f"📦 Cleared fallback cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "redis_available": self.redis_available,
            "fallback_enabled": self.use_fallback
        }
        
        if self.redis_available:
            try:
                keys = self.redis_client.keys("cache:*")
                stats["redis_entries"] = len(keys)
                stats["redis_memory_used"] = self.redis_client.info("memory").get("used_memory_human", "N/A")
            except Exception as e:
                stats["redis_error"] = str(e)
        
        if self.use_fallback:
            stats["fallback_entries"] = len(self.fallback_cache)
        
        return stats
    
    def _generate_cache_key(self, query_text: str) -> str:
        """
        Generate a global cache key from query text (not user-specific).
        
        Args:
            query_text: The natural language query
            
        Returns:
            Cache key string
        """
        # Normalize query text (lowercase, strip whitespace)
        normalized_query = query_text.lower().strip()
        
        # Global cache - no user isolation
        return f"cache:global:query:{normalized_query}"
    
    def _save_fallback_cache(self):
        """Save the fallback cache to disk using joblib."""
        try:
            import joblib
            cache_path = self.cache_dir / "query_cache.joblib"
            joblib.dump(self.fallback_cache, cache_path)
        except Exception as e:
            print(f"⚠️ Failed to save fallback cache: {str(e)}")
    
    def _load_fallback_cache(self):
        """Load the fallback cache from disk using joblib."""
        try:
            import joblib
            cache_path = self.cache_dir / "query_cache.joblib"
            if cache_path.exists():
                self.fallback_cache = joblib.load(cache_path)
                print(f"📦 Loaded {len(self.fallback_cache)} entries from fallback cache")
        except Exception as e:
            print(f"⚠️ Failed to load fallback cache: {str(e)}")
            self.fallback_cache = {}
