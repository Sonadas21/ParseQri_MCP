# Claude Desktop Configuration Guide

## Setup for Windows

### 1. Locate Config File

Open or create the file at:
```
%APPDATA%\Claude\claude_desktop_config.json
```

Full path example:
```
C:\Users\YourUsername\AppData\Roaming\Claude\claude_desktop_config.json
```

### 2. Add CSV MCP Server Configuration

**Option A: Using Virtual Environment**

```json
{
  "mcpServers": {
    "csv-agent": {
      "command": "d:\\Projects\\C2CAS_Projects\\Deployable\\ParseQri_MCP\\CSV_MCP\\.venv\\Scripts\\python.exe",
      "args": [
        "d:\\Projects\\C2CAS_Projects\\Deployable\\ParseQri_MCP\\CSV_MCP\\server.py"
      ]
    }
  }
}
```

**Option B: Using System Python**

```json
{
  "mcpServers": {
    "csv-agent": {
      "command": "python",
      "args": [
        "d:\\Projects\\C2CAS_Projects\\Deployable\\ParseQri_MCP\\CSV_MCP\\server.py"
      ],
      "env": {
        "PYTHONPATH": "d:\\Projects\\C2CAS_Projects\\Deployable\\ParseQri_MCP\\CSV_MCP"
      }
    }
  }
}
```

### 3. Restart Claude Desktop

Close and reopen Claude Desktop completely.

### 4. Verify Connection

In Claude Desktop, you should see:
- A tools/MCP icon in the interface
- "csv-agent" listed as an available server
- 4 tools available: upload_csv, query_data, delete_data, list_tables

---

## For Other MCP Clients

Most MCP clients use similar configuration format:

```json
{
  "command": "python",
  "args": ["path/to/server.py"],
  "env": {}
}
```

---

## Remote Access (HTTP/SSE)

For remote access, use `server_http.py` instead:

### Install Additional Dependency

```bash
pip install uvicorn
```

### Run HTTP Server

```bash
python server_http.py
```

This starts the server at:
- **URL**: `http://localhost:8000`
- **SSE Endpoint**: `http://localhost:8000/sse`

### Access from Network

To allow access from other machines:
- The server binds to `0.0.0.0:8000`
- Access via your machine's IP: `http://YOUR_IP:8000`
- Configure firewall to allow port 8000

---

## Troubleshooting

### Tools Not Showing Up

1. Check config file syntax (valid JSON)
2. Verify file paths are absolute and use double backslashes
3. Restart Claude Desktop completely
4. Check Claude Desktop logs

### Import Errors

1. Ensure virtual environment is activated
2. Install all requirements: `pip install -r requirements.txt`
3. Verify CSV_Agent is in parent directory

### Database Connection Issues

1. Ensure PostgreSQL is running
2. Verify credentials in `../CSV_Agent/config.json`
3. Check Ollama is running for LLM features

---

## Quick Test

Once configured, try this in Claude Desktop:

> "Use the csv-agent to list tables for user_id: test_user"

If working, Claude will call the `list_tables` tool automatically!
