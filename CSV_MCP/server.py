"""
CSV MCP Server

A Model Context Protocol (MCP) server that exposes CSV data processing capabilities
from the CSV_Agent system. Provides tools for uploading CSV files, querying data with
natural language, and deleting data from PostgreSQL and ChromaDB.

Usage:
    # For Claude Desktop (stdio mode - default)
    python server.py
    
    # For HTTP/SSE remote access
    python server.py --http
    python server.py --http --host 0.0.0.0 --port 8000
"""

import sys
import os
import argparse
from pathlib import Path
from typing import Optional, Dict, Any
import json

# Add CSV_Agent to the path
csv_agent_path = Path(__file__).parent.parent / "CSV_Agent"
sys.path.insert(0, str(csv_agent_path))

# Add current directory to path to ensure local imports work
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from mcp.server.fastmcp import FastMCP
from core.orchestrator import TextSQLOrchestrator

# Import from local utils package (must be after path setup)
from utils.db_helper import delete_user_table, list_user_tables

# Initialize FastMCP server
mcp = FastMCP("CSV MCP Server")

# Global orchestrator instance
orchestrator: Optional[TextSQLOrchestrator] = None


def get_orchestrator() -> TextSQLOrchestrator:
    """Get or create the orchestrator instance."""
    global orchestrator
    if orchestrator is None:
        # Load config from CSV_Agent
        config_path = csv_agent_path / "config.json"
        orchestrator = TextSQLOrchestrator(str(config_path))
    return orchestrator


@mcp.tool()
def upload_csv(
    file_path: str,
    table_name: Optional[str] = None,
    user_id: str = "default_user"
) -> Dict[str, Any]:
    """
    Upload and process a CSV file into the PostgreSQL database.
    
    Simply provide the file path and optionally a table name.
    The file will be uploaded and made queryable immediately.
    
    Args:
        file_path: Path to the CSV file (you can drag-drop file to terminal to get path)
        table_name: Optional name for the table (defaults to filename)
        user_id: Optional user identifier (defaults to "default_user")
    
    Returns:
        Dictionary with upload status and table information
    
    Example:
        upload_csv(file_path="d:/data/customers.csv")
        upload_csv(file_path="d:/data/customers.csv", table_name="my_customers")
    """
    try:
        # Validate file path
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"File not found: {file_path}",
                "error": "FILE_NOT_FOUND"
            }
        
        if not file_path.lower().endswith('.csv'):
            return {
                "success": False,
                "message": "File must be a CSV file",
                "error": "INVALID_FILE_TYPE"
            }
        
        # Validate user_id
        if not user_id or not user_id.strip():
            return {
                "success": False,
                "message": "User ID is required",
                "error": "MISSING_USER_ID"
            }
        
        # Process upload through orchestrator
        orch = get_orchestrator()
        context = orch.process_upload(
            csv_file=file_path,
            user_id=user_id.strip(),
            suggested_table_name=table_name
        )
        
        # Extract results
        if hasattr(context, 'error') and context.error:
            return {
                "success": False,
                "message": f"Upload failed: {context.error}",
                "error": "UPLOAD_FAILED"
            }
        
        return {
            "success": True,
            "message": f"CSV uploaded successfully to table: {context.table_name}",
            "table_name": context.table_name,
            "user_id": user_id,
            "file_processed": file_path
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error uploading CSV: {str(e)}",
            "error": "EXCEPTION",
            "error_details": str(e)
        }


@mcp.tool()
def query_data(
    query: str,
    table_name: Optional[str] = None,
    user_id: str = "default_user"
) -> Dict[str, Any]:
    """
    Ask questions about your uploaded CSV data in plain English.
    
    The system automatically finds the right table using semantic search!
    You only need to specify table_name if you have multiple tables and want a specific one.
    
    Args:
        query: Your question in natural language (e.g., "show all customers from New York")
        table_name: Optional - specify if you want a particular table (auto-detected otherwise)
        user_id: Optional user identifier (defaults to "default_user")
    
    Returns:
        Dictionary with query results and formatted response
    
    Example:
        query_data(query="show top 10 rows")  # Auto-finds table!
        query_data(query="what's the average age?", table_name="customers")  # Explicit
    """
    try:
        # Validate inputs
        if not query or not query.strip():
            return {
                "success": False,
                "message": "Query is required",
                "error": "MISSING_QUERY"
            }
        
        if not user_id or not user_id.strip():
            return {
                "success": False,
                "message": "User ID is required",
                "error": "MISSING_USER_ID"
            }
        
        # Use empty string if table_name not provided - let metadata indexer find it
        if not table_name:
            table_name = ""
            print(f"[Query] No table specified, will use semantic search to find relevant table", file=sys.stderr)
        
        # Log query start
        print(f"[Query] Starting query: {query[:50]}...", file=sys.stderr)
        
        # Process query through orchestrator
        orch = get_orchestrator()
        
        print(f"[Query] Processing with orchestrator...", file=sys.stderr)
        context = orch.process_query(
            user_question=query.strip(),
            db_name="",
            table_name=table_name.strip() if table_name else "",
            user_id=user_id.strip()
        )
        
        print(f"[Query] Processing complete", file=sys.stderr)
        
        # Extract results
        if hasattr(context, 'error') and context.error:
            return {
                "success": False,
                "message": f"Query failed: {context.error}",
                "error": "QUERY_FAILED"
            }
        
        # Get the formatted natural language response (primary output)
        formatted_answer = None
        if hasattr(context, 'formatted_response') and context.formatted_response:
            formatted_answer = context.formatted_response
        
        # Get raw query results
        query_results = None
        row_count = 0
        if hasattr(context, 'query_results') and context.query_results is not None:
            # Convert DataFrame to dict if needed
            if hasattr(context.query_results, 'to_dict'):
                query_results = context.query_results.to_dict('records')
                row_count = len(context.query_results)
            else:
                query_results = context.query_results
                row_count = len(context.query_results) if isinstance(context.query_results, list) else 0
        
        # Format results with natural language answer as primary response
        result = {
            "success": True,
            "answer": formatted_answer or "Query executed successfully",  # Primary natural language answer
            "sql_query": getattr(context, 'sql_query', None),
            "results": query_results,
            "row_count": row_count,
            "user_id": user_id,
            "table_name": getattr(context, 'table_name', table_name)  # Return actual table used
        }
        
        print(f"[Query] Returning {row_count} rows with formatted answer", file=sys.stderr)
        return result
        
    except Exception as e:
        print(f"[Query] Error: {str(e)}", file=sys.stderr)
        return {
            "success": False,
            "message": f"Error executing query: {str(e)}",
            "error": "EXCEPTION",
            "error_details": str(e)
        }


@mcp.tool()
def delete_data(
    table_name: str,
    confirm: bool = False,
    user_id: str = "default_user"
) -> Dict[str, Any]:
    """
    Delete uploaded CSV data and metadata. PERMANENT action!
    
    Args:
        table_name: Name of the table to delete
        confirm: Must be True to actually delete (safety check)
        user_id: Optional user identifier (defaults to "default_user")
    
    Returns:
        Deletion status and details
    
    Example:
        delete_data(table_name="customers", confirm=True)
    """
    try:
        # Validate inputs
        if not user_id or not user_id.strip():
            return {
                "success": False,
                "message": "User ID is required",
                "error": "MISSING_USER_ID"
            }
        
        if not table_name or not table_name.strip():
            return {
                "success": False,
                "message": "Table name is required",
                "error": "MISSING_TABLE_NAME"
            }
        
        # Safety check
        if not confirm:
            return {
                "success": False,
                "message": "Deletion not confirmed. Set confirm=True to delete data.",
                "error": "NOT_CONFIRMED",
                "warning": "This action is permanent and cannot be undone!"
            }
        
        # Get config for database connection
        config_path = csv_agent_path / "config.json"
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Delete table and metadata
        success, message, details = delete_user_table(
            user_id=user_id.strip(),
            table_name=table_name.strip(),
            config=config
        )
        
        if success:
            return {
                "success": True,
                "message": message,
                "user_id": user_id,
                "table_name": table_name,
                **details
            }
        else:
            return {
                "success": False,
                "message": message,
                "error": "DELETION_FAILED",
                **details
            }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error deleting data: {str(e)}",
            "error": "EXCEPTION",
            "error_details": str(e)
        }


@mcp.tool()
def list_tables(user_id: str = "default_user") -> Dict[str, Any]:
    """
    List all your uploaded CSV tables.
    
    Args:
        user_id: Optional user identifier (defaults to "default_user")
    
    Returns:
        List of available tables
    
    Example:
        list_tables()
    """
    try:
        if not user_id or not user_id.strip():
            return {
                "success": False,
                "message": "User ID is required",
                "error": "MISSING_USER_ID"
            }
        
        # Get config
        config_path = csv_agent_path / "config.json"
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # List tables
        tables = list_user_tables(user_id.strip(), config)
        
        return {
            "success": True,
            "user_id": user_id,
            "tables": tables,
            "count": len(tables)
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error listing tables: {str(e)}",
            "error": "EXCEPTION",
            "error_details": str(e)
        }


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="CSV MCP Server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run in HTTP/SSE mode (experimental)"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to in HTTP mode (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to in HTTP mode (default: 8000)"
    )
    
    args = parser.parse_args()
    
    if args.http:
        # HTTP/SSE mode using environment variables
        import os
        os.environ['MCP_TRANSPORT'] = 'sse'
        os.environ['MCP_SSE_HOST'] = args.host
        os.environ['MCP_SSE_PORT'] = str(args.port)
        
        print("=" * 60, file=sys.stderr)
        print("CSV MCP Server - HTTP/SSE Mode", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(f"Server URL: http://{args.host}:{args.port}", file=sys.stderr)
        print(f"SSE Endpoint: http://{args.host}:{args.port}/sse", file=sys.stderr)
        print("Available Tools: upload_csv, query_data, delete_data, list_tables", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        
        # Run with SSE transport
        mcp.run(transport='sse')
    else:
        # Stdio mode for Claude Desktop (default)
        print("CSV MCP Server - Stdio Mode", file=sys.stderr)
        print("Use with Claude Desktop or MCP clients", file=sys.stderr)
        mcp.run()

