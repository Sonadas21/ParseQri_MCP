"""
Redis Cache Testing Script

This script tests the Redis cache implementation with LLM response storage.
It verifies:
1. Redis connection
2. Cache write operations
3. Cache read operations
4. Fallback to joblib
5. Cache statistics
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.redis_cache import RedisCacheAgent
from models.data_models import QueryContext
import pandas as pd

def test_redis_connection():
    """Test Redis connection"""
    print("\n" + "="*60)
    print("TEST 1: Redis Connection")
    print("="*60)
    
    cache = RedisCacheAgent(
        redis_host="localhost",
        redis_port=6379,
        use_fallback=True
    )
    
    if cache.redis_available:
        print("✅ Redis connection successful")
    else:
        print("⚠️ Redis not available, using fallback")
    
    return cache

def test_cache_write(cache):
    """Test caching a query with complete data"""
    print("\n" + "="*60)
    print("TEST 2: Cache Write (with LLM Response)")
    print("="*60)
    
    # Create a sample query context
    context = QueryContext(
        user_question="How many customers are there?",
        db_name="parseqri",
        table_name="customers_default_user",
        user_id="test_user",
        sql_query="SELECT COUNT(*) as total FROM customers_default_user;",
        formatted_response="There are 150 customers in the database.",
        query_results=pd.DataFrame({
            "total": [150]
        })
    )
    
    # Cache the query
    cache.cache_query(context)
    print("✅ Cached query with:")
    print(f"   - SQL Query: {context.sql_query}")
    print(f"   - LLM Response: {context.formatted_response}")
    print(f"   - Results: {len(context.query_results)} row(s)")

def test_cache_read(cache):
    """Test retrieving cached data"""
    print("\n" + "="*60)
    print("TEST 3: Cache Read")
    print("="*60)
    
    # Try to retrieve the cached query
    cached_data = cache.get_cached_entry(
        "How many customers are there?",
        "test_user"
    )
    
    if cached_data:
        print("✅ Cache hit!")
        print(f"   - SQL Query: {cached_data.get('sql_query')}")
        print(f"   - LLM Response: {cached_data.get('formatted_response')}")
        print(f"   - Timestamp: {cached_data.get('timestamp')}")
        
        if 'query_results' in cached_data:
            print(f"   - Results: {len(cached_data['query_results'])} row(s)")
    else:
        print("❌ Cache miss")

def test_cache_miss(cache):
    """Test cache miss scenario"""
    print("\n" + "="*60)
    print("TEST 4: Cache Miss")
    print("="*60)
    
    cached_data = cache.get_cached_entry(
        "This question was never asked before",
        "test_user"
    )
    
    if cached_data is None:
        print("✅ Correctly returned None for non-existent query")
    else:
        print("❌ Unexpected cache hit")

def test_user_isolation(cache):
    """Test that different users have separate caches"""
    print("\n" + "="*60)
    print("TEST 5: User Isolation")
    print("="*60)
    
    # Cache for user1
    context_user1 = QueryContext(
        user_question="Show all orders",
        db_name="parseqri",
        table_name="orders_user1",
        user_id="user1",
        sql_query="SELECT * FROM orders_user1 LIMIT 10;",
        formatted_response="Here are the latest 10 orders for user1."
    )
    cache.cache_query(context_user1)
    print("✅ Cached query for user1")
    
    # Try to retrieve for user2 (should be cache miss)
    cached_data = cache.get_cached_entry("Show all orders", "user2")
    
    if cached_data is None:
        print("✅ User isolation working - user2 cannot access user1's cache")
    else:
        print("❌ User isolation failed - cache leaked between users")
    
    # Retrieve for user1 (should be cache hit)
    cached_data = cache.get_cached_entry("Show all orders", "user1")
    if cached_data:
        print("✅ User1 can access their own cache")

def test_cache_stats(cache):
    """Test cache statistics"""
    print("\n" + "="*60)
    print("TEST 6: Cache Statistics")
    print("="*60)
    
    stats = cache.get_cache_stats()
    
    print("Cache Statistics:")
    for key, value in stats.items():
        print(f"   - {key}: {value}")

def test_ttl(cache):
    """Test TTL (Time-To-Live) functionality"""
    print("\n" + "="*60)
    print("TEST 7: TTL (Time-To-Live)")
    print("="*60)
    
    if cache.redis_available:
        import redis
        
        # Create a cache entry with 5 second TTL
        cache_short_ttl = RedisCacheAgent(
            redis_host="localhost",
            redis_port=6379,
            ttl_seconds=5,  # 5 seconds
            use_fallback=False
        )
        
        context = QueryContext(
            user_question="Test TTL query",
            db_name="parseqri",
            table_name="test",
            user_id="ttl_user",
            sql_query="SELECT 1;",
            formatted_response="TTL test response"
        )
        
        cache_short_ttl.cache_query(context)
        print("✅ Cached query with 5 second TTL")
        
        # Check TTL
        cache_key = cache_short_ttl._generate_cache_key("Test TTL query", "ttl_user")
        ttl = cache_short_ttl.redis_client.ttl(cache_key)
        print(f"   - Remaining TTL: {ttl} seconds")
        
        if ttl > 0 and ttl <= 5:
            print("✅ TTL is working correctly")
        else:
            print("⚠️ TTL value unexpected")
    else:
        print("⚠️ Skipping TTL test (Redis not available)")

def test_clear_cache(cache):
    """Test cache clearing"""
    print("\n" + "="*60)
    print("TEST 8: Clear Cache")
    print("="*60)
    
    # Clear user-specific cache
    cache.clear_cache(user_id="test_user")
    print("✅ Cleared cache for test_user")
    
    # Verify cache is empty for test_user
    cached_data = cache.get_cached_entry(
        "How many customers are there?",
        "test_user"
    )
    
    if cached_data is None:
        print("✅ Cache successfully cleared")
    else:
        print("❌ Cache still contains data")

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("REDIS CACHE TEST SUITE")
    print("="*60)
    
    try:
        # Test 1: Connection
        cache = test_redis_connection()
        
        # Test 2: Write
        test_cache_write(cache)
        
        # Test 3: Read
        test_cache_read(cache)
        
        # Test 4: Cache Miss
        test_cache_miss(cache)
        
        # Test 5: User Isolation
        test_user_isolation(cache)
        
        # Test 6: Statistics
        test_cache_stats(cache)
        
        # Test 7: TTL
        test_ttl(cache)
        
        # Test 8: Clear Cache
        test_clear_cache(cache)
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()
