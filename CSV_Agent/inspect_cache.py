import redis
import pickle

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)

# Get all keys first
all_keys = r.keys("cache:*")
print("=== All Cache Keys ===")
for key in all_keys:
    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
    print(key_str)

if all_keys:
    # Inspect the first key
    first_key = all_keys[0]
    first_key_str = first_key.decode('utf-8') if isinstance(first_key, bytes) else first_key
    print(f"\n=== Inspecting: {first_key_str} ===")
    
    cached_data = r.get(first_key)


    
    if cached_data:
        # Unpickle the data
        data = pickle.loads(cached_data)
        
        print("=== Cached Data ===")
        print(f"user_id: {data.get('user_id')}")
        print(f"table_name: {data.get('table_name')}")
        print(f"sql_query: {data.get('sql_query')}")
        print(f"timestamp: {data.get('timestamp')}")
        if data.get('formatted_response'):
            print(f"\nFormatted Response:\n{data.get('formatted_response')[:200]}...")
    else:
        print("No data found for this key")
else:
    print("\nNo cache entries found")