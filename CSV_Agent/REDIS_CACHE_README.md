# Redis Cache with Enhanced LLM Response Storage

## Quick Start

### Option 1: Docker (Recommended) 🐳

**Start Redis:**
```powershell
cd d:\Projects\C2CAS_Projects\Deployable\ParseQri_MCP\CSV_Agent
.\redis-docker.bat start
```

**Verify:**
```powershell
docker exec -it parseqri_redis_cache redis-cli ping
# Should return: PONG
```

**Use with cache:**
```powershell
python main.py --config config_redis.json --query "Your question" --user your_user_id
```

### Option 2: Windows Installation

See detailed instructions in the full guide: [Redis Setup Guide](redis_setup_guide.md)

---

## What's Cached?

The enhanced cache now stores:

| Item | Description |
|------|-------------|
| **User Question** | Original natural language query |
| **SQL Query** | Generated SQL statement |
| **LLM Response** ✨ | Formatted natural language answer |
| **Query Results** | DataFrame results (optional) |
| **Metadata** | User ID, timestamp, table name |

**Before (old cache):**
```
Cache hit → Execute SQL → Format response → Return
```

**Now (enhanced cache):**
```
Cache hit → Return immediately ✅
```

---

## Features

✅ **Complete Response Caching** - No re-execution needed  
✅ **Automatic Fallback** - Uses joblib if Redis unavailable  
✅ **User Isolation** - Separate cache per user  
✅ **TTL Support** - Auto-expire after 24 hours  
✅ **Thread-Safe** - Handles concurrent requests  
✅ **Docker Ready** - Easy deployment  

---

## File Structure

```
CSV_Agent/
├── agents/
│   ├── redis_cache.py          # Redis cache implementation
│   └── query_cache.py          # Joblib fallback
├── config_redis.json           # Redis configuration
├── docker-compose.redis.yml    # Docker setup
├── redis.conf                  # Redis server config
├── redis-docker.bat           # Windows management script
├── redis-docker.sh            # Linux management script
└── tests/
    └── test_redis_cache.py    # Test suite
```

---

## Configuration

Edit `config_redis.json`:

```json
{
  "query_cache": {
    "module": "agents.redis_cache",
    "class": "RedisCacheAgent",
    "params": {
      "redis_host": "localhost",
      "redis_port": 6379,
      "redis_db": 0,
      "ttl_seconds": 86400,
      "use_fallback": true,
      "cache_dir": "cache"
    }
  }
}
```

---

## Testing

```powershell
# Run test suite
python tests\test_redis_cache.py

# Test with actual query
python main.py --config config_redis.json --query "Show all customers" --user test_user

# Run same query again (should hit cache)
python main.py --config config_redis.json --query "Show all customers" --user test_user
```

Expected output on cache hit:
```
✅ Cache hit! Returning cached response (saved execution + formatting)
```

---

## Management

### Docker Commands

```powershell
# Start
.\redis-docker.bat start

# Stop
.\redis-docker.bat stop

# View logs
.\redis-docker.bat logs

# With GUI
.\redis-docker.bat gui
# Open http://localhost:8081
```

### Redis CLI

```powershell
# Access Redis CLI
docker exec -it parseqri_redis_cache redis-cli

# View all cached queries
KEYS cache:*

# Check cache size
DBSIZE

# Clear all cache
FLUSHDB
```

---

## Performance

| Metric | Redis | Joblib |
|--------|-------|--------|
| Cache Write | 2-3ms | 50-100ms |
| Cache Read | 1-2ms | 0.1-1ms |
| Startup | Instant | 1-5s |
| Concurrent | ✅ Safe | ❌ Race conditions |
| Distributed | ✅ Multi-instance | ❌ Single only |
| TTL | ✅ Built-in | ❌ Manual |

---

## Troubleshooting

### Redis not connecting?

1. Check Docker is running:
   ```powershell
   docker ps
   ```

2. Start Redis:
   ```powershell
   .\redis-docker.bat start
   ```

3. Verify connection:
   ```powershell
   docker exec -it parseqri_redis_cache redis-cli ping
   ```

### Automatic Fallback

If Redis is unavailable, the system automatically uses joblib:

```
⚠️ Redis connection failed: Connection refused
📦 Falling back to joblib cache
```

No action needed - everything continues to work!

---

## Full Guides

- **Docker Setup**: [redis_docker_guide.md](redis_docker_guide.md)
- **Windows Installation**: [redis_setup_guide.md](redis_setup_guide.md)
- **Implementation Details**: [implementation_plan.md](implementation_plan.md)
