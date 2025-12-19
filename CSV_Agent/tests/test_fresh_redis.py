"""Test the fresh Redis cache implementation"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.redis_cache import RedisCacheAgent
from models.data_models import QueryContext
import pandas as pd

print("=" * 60)
print("TESTING FRESH REDIS CACHE")
print("=" * 60)

# Test 1: Initialize cache
print("\n[TEST 1] Initialize Redis Cache")
cache = RedisCacheAgent(
    redis_host="localhost",
    redis_port=6379,
    ttl_seconds=3600
)

if not cache.redis_available:
    print("❌ Redis not available - check if Redis is running")
    sys.exit(1)

# Test 2: Cache miss (first query)
print("\n[TEST 2] Cache Miss Test")
context = QueryContext(
    user_question="How many customers are there?",
    db_name="parseqri",
    table_name="customers"
)
response = cache.process(context)
print(f"Cache hit: {response.data.get('cache_hit')}")
assert response.data.get('cache_hit') == False, "Should be cache miss"
print("✅ Cache miss working correctly")

# Test 3: Save to cache
print("\n[TEST 3] Cache Save Test")
context.sql_query = "SELECT COUNT(*) FROM customers;"
context.formatted_response = "There are 150 customers in the database."
context.query_results = pd.DataFrame({"count": [150]})
cache.cache_query(context)
print("✅ Data cached")

# Test 4: Cache hit (same query)
print("\n[TEST 4] Cache Hit Test")
context2 = QueryContext(
    user_question="How many customers are there?",
    db_name="parseqri",
    table_name="customers"
)
response2 = cache.process(context2)
print(f"Cache hit: {response2.data.get('cache_hit')}")
assert response2.data.get('cache_hit') == True, "Should be cache hit"

cached_data = response2.data.get('cached_data')
print(f"SQL Query: {cached_data.get('sql_query')}")
print(f"Response: {cached_data.get('formatted_response')}")
print("✅ Cache hit working correctly")

# Test 5: Cache stats
print("\n[TEST 5] Cache Statistics")
stats = cache.get_stats()
print(f"Total entries: {stats.get('total_entries')}")
print(f"Memory used: {stats.get('memory_used')}")
print("✅ Stats retrieved")

# Test 6: Different query (cache miss)
print("\n[TEST 6] Different Query (Cache Miss)")
context3 = QueryContext(
    user_question="Show me all products",
    db_name="parseqri",
    table_name="products"
)
response3 = cache.process(context3)
print(f"Cache hit: {response3.data.get('cache_hit')}")
assert response3.data.get('cache_hit') == False, "Should be cache miss for different query"
print("✅ Different query = cache miss")

print("\n" + "=" * 60)
print("ALL TESTS PASSED! ✅")
print("=" * 60)
