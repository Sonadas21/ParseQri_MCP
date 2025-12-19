# Troubleshooting MCP Timeout Errors

## Error: MCP -32001 Request Timed Out

This error occurs when query processing takes longer than the MCP client's timeout (usually 60 seconds).

### Common Causes

1. **Ollama LLM is slow** - The CSV_Agent uses local LLMs via Ollama for query processing
2. **Large datasets** - Processing many rows can be slow
3. **Complex queries** - Natural language processing takes time
4. **Cold start** - First query loads models and initializes agents

### Solutions

#### Option 1: Increase Client Timeout (Recommended)

If using **Claude Desktop**, edit your config:

```json
{
  "mcpServers": {
    "csv-agent": {
      "command": "python",
      "args": ["path/to/server.py"],
      "timeout": 180000  // 3 minutes in milliseconds
    }
  }
}
```

If using **MCP Inspector**, it may have timeout settings in the UI.

#### Option 2: Use Faster LLM Models

Edit `../CSV_Agent/config.json` and change to smaller/faster models:

```json
{
  "agents": {
    "sql_generation": {
      "params": {
        "llm_model": "qwen3:4b"  // Faster than llama3.1:8b
      }
    },
    "intent_classifier": {
      "params": {
        "llm_model": "qwen3:4b"
      }
    }
  }
}
```

**Available fast models:**
- `qwen3:4b` - Fast, good quality
- `phi3:mini` - Very fast, smaller
- `gemma2:2b` - Ultra fast, basic

Pull them with:
```bash
ollama pull qwen3:4b
ollama pull phi3:mini
```

#### Option 3: Optimize Ollama

Make sure Ollama is using GPU acceleration:

```bash
# Check if GPU is being used
ollama ps

# If not using GPU, reinstall Ollama with CUDA/ROCm support
```

#### Option 4: Pre-warm the Server

The first query is always slowest (loading models). Make a simple test query first:

```json
{
  "query": "count rows",
  "table_name": "your_table"
}
```

This loads everything. Subsequent queries will be faster.

#### Option 5: Direct SQL Queries (Advanced)

For complex queries, you can bypass the LLM and use SQL directly:

1. Get the SQL from a successful query
2. Save it for reuse
3. Or modify the CSV_Agent to accept raw SQL

### Monitoring

Watch the server logs for timing information:

```
[Query] Starting query for table 'customers': show top 10...
[Query] Processing with orchestrator...
[Query] Processing complete
[Query] Returning 10 rows
```

If you see the query start but not complete, the timeout is happening during processing.

### Quick Test

Test if Ollama is responsive:

```bash
curl http://localhost:11434/api/tags
```

Should return JSON with installed models.

Test query speed:

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3:4b",
  "prompt": "hello",
  "stream": false
}'
```

Should complete in < 5 seconds for a fast model.

### Best Practice

For production use:
1. Use timeout of 180000ms (3 minutes)
2. Use `qwen3:4b` model for speed
3. GPU-accelerated Ollama if possible
4. Pre-warm with a test query
5. Keep datasets reasonable size (< 100K rows)

### Still Having Issues?

1. Check server logs for errors
2. Verify Ollama models are pulled: `ollama list`
3. Test simple queries first: `"count rows"`
4. Try direct database connection (bypass LLM)
5. Consider using HTTP mode with longer timeouts
