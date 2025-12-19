# ParseQri Multi-User Support

This document explains how to use the user-based metadata indexing and data management features in ParseQri.

## Overview

The multi-user support implementation allows:

1. Storing data in PostgreSQL tables with user-specific columns
2. Indexing metadata in ChromaDB with user context
3. Restricting queries to only the relevant user's data
4. Supporting multiple users with their own private datasets

## Requirements

In addition to the standard ParseQri requirements, you'll need:

- PostgreSQL server (local or remote)
- ChromaDB (installed via pip)
- SQLAlchemy for database operations
- psycopg2-binary for PostgreSQL connection

Install the dependencies with:

```bash
pip install -r requirements.txt
```

## Configuration

The `config.json` file includes the necessary configuration for PostgreSQL and ChromaDB. Make sure to update the connection details:

```json
"postgres_handler": {
    "module": "agents.postgres_handler",
    "class": "PostgresHandlerAgent", 
    "params": {
        "db_url": "postgresql://postgres:password@localhost:5432/parseqri",
        "schema": "public"
    }
},
"metadata_indexer": {
    "module": "agents.metadata_indexer",
    "class": "MetadataIndexerAgent",
    "params": {
        "llm_model": "llama3.1",
        "api_base": "http://localhost:11434",
        "chroma_persist_dir": "../data/chromadb"
    }
}
```

## Usage

### Data Upload

To upload data for a specific user:

```bash
python main.py --upload path/to/file.csv --user user123 --table optional_table_name
```

This will:
1. Extract metadata using an LLM
2. Store the metadata in ChromaDB with the user_id
3. Create a PostgreSQL table with user_id as the first column
4. Load the data into PostgreSQL

### Querying Data

To query a specific user's data:

```bash
python main.py "What's the average sales by product category?" --user user123
```

The system will:
1. Search ChromaDB for relevant tables associated with the user
2. Generate SQL with user_id filtering
3. Execute the query against PostgreSQL with user context
4. Return only the results for that specific user

### Listing User Tables

To list all tables available for a user:

```bash
python main.py --list-tables --user user123
```

## How It Works

### Metadata Indexing

The `MetadataIndexerAgent` handles extracting metadata from uploaded CSV files and storing it in ChromaDB with the user_id as part of the metadata. When searching for relevant tables, it filters results to only include entries matching the current user_id.

### PostgreSQL Integration

The `PostgresHandlerAgent` creates tables with the user_id as the first column and ensures all queries include a `WHERE user_id = 'xyz'` condition. Table names are also prefixed with the user_id to avoid conflicts.

### Query Routing

The `QueryRouterAgent` helps coordinate the process by suggesting the right sequence of agents to handle each query, ensuring user context is maintained throughout the pipeline.

## Example

See the included demo script for a complete example:

```bash
python examples/multi_user_demo.py
```

This will:
1. Create sample data for two users
2. Upload and index the data with user context
3. Run queries for each user separately
4. Demonstrate the security of data isolation

## Security Considerations

- All queries are automatically filtered by user_id
- Tables are prefixed with user_id for additional isolation
- Metadata searches are restricted to the current user
- Cross-user data access attempts are prevented 