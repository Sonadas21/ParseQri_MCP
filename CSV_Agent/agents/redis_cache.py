"""
Fresh Redis Cache Implementation
Simple, clean caching for CSV Agent queries
"""
import redis
import json
import pickle
from typing import Optional, Dict, Any
from datetime import datetime
from models.data_models import QueryContext, AgentResponse


class RedisCacheAgent:
    """Simple Redis cache for query responses."""
    
    def __init__(self, 
                 redis_host: str = "localhost",
                 redis_port: int = 6379,
                 redis_db: int = 0,
                 ttl_seconds: int = 86400,  # 24 hours
                 **kwargs):  # Accept other params for compatibility
        """
        Initialize Redis cache.
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            ttl_seconds: Cache expiration time in seconds
        """
        self.ttl_seconds = ttl_seconds
        self.redis_client = None
        self.redis_available = False
        
        # Connect to Redis
        self._connect(redis_host, redis_port, redis_db)
    
    def _connect(self, host: str, port: int, db: int):
        """Connect to Redis server."""
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=False,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # Test connection
            self.redis_client.ping()
            self.redis_available = True
            print(f"✅ Redis connected at {host}:{port}")
        except Exception as e:
            self.redis_available = False
            print(f"⚠️ Redis unavailable: {str(e)}")
    
    def process(self, context: QueryContext) -> AgentResponse:
        """Check if query is in cache."""
        if not self.redis_available:
            return AgentResponse(
                success=True,
                message="Cache unavailable",
                data={"cache_hit": False}
            )
        
        try:
            # Generate cache key
            cache_key = self._make_key(context.user_question)
            
            # Try to get from cache
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                # Deserialize
                cache_entry = pickle.loads(cached_data)
                print(f"✅ Cache HIT for: {context.user_question[:50]}...")
                
                return AgentResponse(
                    success=True,
                    message="Cache hit",
                    data={
                        "cache_hit": True,
                        "cached_data": cache_entry
                    }
                )
            else:
                print(f"❌ Cache MISS for: {context.user_question[:50]}...")
                return AgentResponse(
                    success=True,
                    message="Cache miss",
                    data={"cache_hit": False}
                )
                
        except Exception as e:
            print(f"⚠️ Cache check error: {str(e)}")
            return AgentResponse(
                success=True,
                message="Cache check failed",
                data={"cache_hit": False}
            )
    
    def cache_query(self, context: QueryContext):
        """Save query response to cache."""
        if not self.redis_available or not context.sql_query:
            return
        
        try:
            # Prepare cache entry
            cache_entry = {
                "sql_query": context.sql_query,
                "formatted_response": context.formatted_response,
                "table_name": context.table_name,
                "db_name": context.db_name,
                "timestamp": datetime.now().isoformat()
            }
            
            # Include query results if available
            if hasattr(context, 'query_results') and context.query_results is not None:
                try:
                    if not context.query_results.empty:
                        cache_entry["query_results"] = context.query_results.to_dict('records')
                        cache_entry["row_count"] = len(context.query_results)
                except:
                    pass
            
            # Generate cache key
            cache_key = self._make_key(context.user_question)
            
            # Serialize and save
            serialized = pickle.dumps(cache_entry)
            self.redis_client.setex(cache_key, self.ttl_seconds, serialized)
            
            print(f"💾 Cached: {context.user_question[:50]}... (TTL: {self.ttl_seconds}s)")
            
        except Exception as e:
            print(f"⚠️ Cache save error: {str(e)}")
    
    def _make_key(self, query: str) -> str:
        """Generate cache key from query."""
        # Normalize: lowercase and strip whitespace
        normalized = query.lower().strip()
        # Use simple format
        return f"cache:query:{normalized}"
    
    def clear_cache(self):
        """Clear all cache entries."""
        if not self.redis_available:
            return
        
        try:
            keys = self.redis_client.keys("cache:*")
            if keys:
                self.redis_client.delete(*keys)
                print(f"🗑️ Cleared {len(keys)} cache entries")
        except Exception as e:
            print(f"⚠️ Cache clear error: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.redis_available:
            return {"redis_available": False}
        
        try:
            keys = self.redis_client.keys("cache:*")
            return {
                "redis_available": True,
                "total_entries": len(keys),
                "memory_used": self.redis_client.info("memory").get("used_memory_human", "N/A")
            }
        except Exception as e:
            return {
                "redis_available": False,
                "error": str(e)
            }
