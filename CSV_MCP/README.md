# CSV MCP Server

A Model Context Protocol (MCP) server that exposes CSV data processing capabilities from the CSV_Agent system. This server provides tools for uploading CSV files, querying data with natural language, and managing data in PostgreSQL with ChromaDB metadata indexing.

## Features

- **CSV Upload**: Upload and process CSV files into PostgreSQL with automatic metadata extraction
- **Natural Language Queries**: Query your data using plain English questions
- **Data Deletion**: Clean up uploaded data and associated metadata
- **Multi-User Support**: Isolated data storage per user with user-specific tables
- **Metadata Indexing**: Automatic metadata extraction and ChromaDB indexing for intelligent queries

## Requirements

- Python 3.8+
- PostgreSQL database
- Ollama (for LLM-based features)
- CSV_Agent (in parent directory)
- uvicorn (optional, only for HTTP mode)

## Installation

1. **Install dependencies**:
   ```bash
   cd CSV_MCP
   pip install -r requirements.txt
   
   # For HTTP mode, also install:
   pip install uvicorn
   ```

2. **Configure database connection**:
   - The server uses the configuration from `../CSV_Agent/config.json`
   - Ensure PostgreSQL is running and accessible
   - Update database credentials in the CSV_Agent config if needed

3. **Start Ollama** (if using LLM features):
   ```bash
   ollama serve
   ```

## Running the Server

The server supports two modes:

### Stdio Mode (Default - for Claude Desktop)

```bash
python server.py
```

This mode is used by Claude Desktop and other MCP clients that communicate via stdin/stdout.

### HTTP/SSE Mode (for Remote Access)

```bash
# Install uvicorn first
pip install uvicorn

# Run in HTTP mode
python server.py --http

# Custom host and port
python server.py --http --host 0.0.0.0 --port 8000
```

Access the server at:
- **Server URL**: `http://localhost:8000`
- **SSE Endpoint**: `http://localhost:8000/sse`

### Using MCP Inspector

For testing:

```bash
python server.py
```

Or use with MCP Inspector for testing:

```bash
npx @modelcontextprotocol/inspector python server.py
```

## MCP Tools

### 1. upload_csv

Upload and process a CSV file into the database.

**Parameters**:
- `file_path` (str): Absolute path to the CSV file
- `user_id` (str): Unique user identifier (e.g., "john_doe")
- `table_name` (str, optional): Suggested table name (defaults to filename)

**Returns**:
- `success`: Boolean indicating success
- `message`: Result description
- `table_name`: Actual table name created
- `user_id`: User identifier

**Example**:
```json
{
  "file_path": "d:/data/customers.csv",
  "user_id": "john_doe",
  "table_name": "customer_data"
}
```

### 2. query_data

Execute a natural language query against uploaded data.

**Parameters**:
- `query` (str): Natural language query
- `user_id` (str): User identifier who owns the data
- `table_name` (str): Base table name (without user_id suffix)

**Returns**:
- `success`: Boolean indicating success
- `message`: Result description
- `sql_query`: Generated SQL query
- `results`: Query results as list of dictionaries
- `row_count`: Number of rows returned

**Example**:
```json
{
  "query": "show top 10 customers by revenue",
  "user_id": "john_doe",
  "table_name": "customers"
}
```

### 3. delete_data

Delete uploaded CSV data and associated metadata.

**Parameters**:
- `user_id` (str): User identifier who owns the data
- `table_name` (str): Base table name to delete
- `confirm` (bool): Must be `true` to execute (safety check)

**Returns**:
- `success`: Boolean indicating success
- `message`: Result description
- `deleted_table`: Full table name that was deleted
- `postgres_deleted`: Boolean indicating PostgreSQL deletion
- `chromadb_cleaned`: Boolean indicating ChromaDB cleanup

**Example**:
```json
{
  "user_id": "john_doe",
  "table_name": "customers",
  "confirm": true
}
```

### 4. list_tables

List all tables available for a specific user.

**Parameters**:
- `user_id` (str): User identifier

**Returns**:
- `success`: Boolean indicating success
- `user_id`: User identifier
- `tables`: List of base table names
- `count`: Number of tables found

**Example**:
```json
{
  "user_id": "john_doe"
}
```

## Architecture

The CSV MCP Server acts as a bridge between MCP clients and the CSV_Agent system:

```
MCP Client
    ↓
CSV MCP Server (FastMCP)
    ↓
CSV_Agent Orchestrator
    ↓
┌─────────────────┬──────────────────┐
│  PostgreSQL DB  │  ChromaDB        │
│  (CSV Data)     │  (Metadata)      │
└─────────────────┴──────────────────┘
```

### Data Flow

1. **Upload**:
   - CSV file → DataIngestionAgent (validation)
   - MetadataIndexerAgent (LLM extraction)
   - PostgresHandlerAgent (table creation)
   - ChromaDB (metadata storage)

2. **Query**:
   - Natural language → IntentClassificationAgent
   - MetadataIndexerAgent (find relevant tables)
   - SQLGenerationAgent (create SQL)
   - QueryExecutionAgent (run query)
   - ResponseFormattingAgent (format results)

3. **Delete**:
   - PostgreSQL (DROP TABLE)
   - ChromaDB (delete metadata)
   - Cleanup metadata JSON files

## Configuration

The server uses `../CSV_Agent/config.json` for database and LLM settings. Key configuration sections:

- **PostgreSQL**: Connection URL and schema
- **ChromaDB**: Persistence directory for metadata
- **LLM Models**: Ollama models for different agents

## Multi-User Support

Each user gets isolated data storage:

- Tables are prefixed with user_id: `{table_name}_{user_id}`
- ChromaDB collections are user-specific: `{user_id}_metadata`
- Metadata is stored in user directories: `db_storage/{user_id}/`

## Troubleshooting

### Connection Issues

- **PostgreSQL**: Verify database is running and credentials are correct
- **Ollama**: Ensure Ollama is running on port 11434
- **ChromaDB**: Check write permissions for metadata directory

### Upload Failures

- Verify CSV file path is absolute and file exists
- Check CSV format (headers, encoding)
- Ensure PostgreSQL has space and permissions

### Query Issues

- Verify table exists using `list_tables` tool
- Check user_id matches the one used during upload
- Ensure table_name doesn't include user_id suffix

## Development

### Project Structure

```
CSV_MCP/
├── server.py           # Main MCP server
├── utils/
│   ├── __init__.py
│   └── db_helper.py    # Database utilities
├── config.json         # Server configuration
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

### Testing

Use the MCP Inspector for interactive testing:

```bash
npx @modelcontextprotocol/inspector python server.py
```

## License

This project is part of the ParseQri MCP suite.

## Support

For issues or questions, refer to the CSV_Agent documentation or contact the development team.
