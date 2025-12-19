"""
Database Helper Utilities

Provides helper functions for database operations including:
- Deleting PostgreSQL tables
- Cleaning up ChromaDB metadata
- Listing user tables
"""

import os
import shutil
from typing import Dict, Any, List, Tuple
from sqlalchemy import create_engine, inspect, text
from pathlib import Path
import chromadb


def delete_user_table(user_id: str, table_name: str, config: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Delete a user's table from PostgreSQL and remove associated metadata from ChromaDB.
    
    Args:
        user_id: User identifier
        table_name: Base table name (without user_id suffix)
        config: Configuration dictionary containing database settings
    
    Returns:
        Tuple of (success, message, details_dict)
    """
    details = {
        "postgres_deleted": False,
        "chromadb_cleaned": False,
        "deleted_table": None
    }
    
    try:
        # Get database configuration
        postgres_config = config.get('agents', {}).get('postgres_handler', {}).get('params', {})
        db_url = postgres_config.get('db_url', 'postgresql://postgres:password@localhost:5432/parseqri')
        schema = postgres_config.get('schema', 'public')
        
        # Construct qualified table name
        qualified_table_name = f"{table_name}_{user_id}"
        qualified_table_name = qualified_table_name[:63]  # PostgreSQL limit
        
        # Delete from PostgreSQL
        try:
            engine = create_engine(db_url)
            with engine.connect() as conn:
                # Check if table exists
                inspector = inspect(engine)
                if qualified_table_name in inspector.get_table_names(schema=schema):
                    # Drop the table
                    conn.execute(text(f'DROP TABLE IF EXISTS "{schema}"."{qualified_table_name}" CASCADE'))
                    conn.commit()
                    details["postgres_deleted"] = True
                    details["deleted_table"] = qualified_table_name
                    print(f"Deleted table: {qualified_table_name}")
                else:
                    return False, f"Table {qualified_table_name} not found in database", details
        except Exception as e:
            return False, f"Error deleting PostgreSQL table: {str(e)}", details
        
        # Clean up ChromaDB metadata
        try:
            # Get ChromaDB configuration
            metadata_config = config.get('agents', {}).get('metadata_indexer', {}).get('params', {})
            chroma_persist_dir = metadata_config.get('chroma_persist_dir', '../data/db_storage')
            
            # Resolve relative path
            if not os.path.isabs(chroma_persist_dir):
                # Assume it's relative to CSV_Agent directory
                csv_agent_dir = Path(__file__).parent.parent / "CSV_Agent"
                chroma_persist_dir = csv_agent_dir / chroma_persist_dir
            
            user_chroma_dir = Path(chroma_persist_dir) / user_id
            
            if user_chroma_dir.exists():
                # Connect to user's ChromaDB
                client = chromadb.PersistentClient(path=str(user_chroma_dir))
                
                try:
                    # Get the collection
                    collection = client.get_collection(f"{user_id}_metadata")
                    
                    # Try to delete the document for this table
                    document_id = f"{table_name}_{user_id}"
                    
                    try:
                        collection.delete(ids=[document_id])
                        details["chromadb_cleaned"] = True
                        print(f"Deleted ChromaDB metadata for document: {document_id}")
                    except Exception as e:
                        print(f"Warning: Could not delete ChromaDB document {document_id}: {e}")
                        # Still consider it a partial success
                        details["chromadb_cleaned"] = "partial"
                    
                    # Also delete the metadata JSON file if it exists
                    metadata_json = user_chroma_dir / f"metadata_{table_name}.json"
                    if metadata_json.exists():
                        metadata_json.unlink()
                        print(f"Deleted metadata JSON file: {metadata_json}")
                        
                except Exception as e:
                    print(f"Warning: Could not access ChromaDB collection: {e}")
                    details["chromadb_cleaned"] = "skipped"
            else:
                print(f"ChromaDB directory not found for user: {user_id}")
                details["chromadb_cleaned"] = "skipped"
                
        except Exception as e:
            print(f"Warning: Error cleaning ChromaDB metadata: {e}")
            details["chromadb_cleaned"] = "failed"
        
        # Overall success if PostgreSQL deletion succeeded
        if details["postgres_deleted"]:
            chromadb_status = "and ChromaDB metadata cleaned" if details["chromadb_cleaned"] == True else ""
            return True, f"Successfully deleted table {qualified_table_name} {chromadb_status}", details
        else:
            return False, "Failed to delete table", details
            
    except Exception as e:
        return False, f"Error during deletion: {str(e)}", details


def list_user_tables(user_id: str, config: Dict[str, Any]) -> List[str]:
    """
    List all tables belonging to a specific user.
    
    Args:
        user_id: User identifier
        config: Configuration dictionary containing database settings
    
    Returns:
        List of base table names (without user_id suffix)
    """
    try:
        # Get database configuration
        postgres_config = config.get('agents', {}).get('postgres_handler', {}).get('params', {})
        db_url = postgres_config.get('db_url', 'postgresql://postgres:password@localhost:5432/parseqri')
        schema = postgres_config.get('schema', 'public')
        
        # Connect to database
        engine = create_engine(db_url)
        inspector = inspect(engine)
        
        # Get all tables in schema
        all_tables = inspector.get_table_names(schema=schema)
        
        # Filter tables by user_id suffix
        user_tables = []
        suffix = f"_{user_id}"
        
        for table in all_tables:
            if table.endswith(suffix):
                # Remove the suffix to get base table name
                base_name = table[:-len(suffix)]
                user_tables.append(base_name)
        
        return user_tables
        
    except Exception as e:
        print(f"Error listing user tables: {e}")
        return []


def get_table_info(user_id: str, table_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get information about a specific user table.
    
    Args:
        user_id: User identifier
        table_name: Base table name (without user_id suffix)
        config: Configuration dictionary containing database settings
    
    Returns:
        Dictionary with table information
    """
    try:
        # Get database configuration
        postgres_config = config.get('agents', {}).get('postgres_handler', {}).get('params', {})
        db_url = postgres_config.get('db_url', 'postgresql://postgres:password@localhost:5432/parseqri')
        schema = postgres_config.get('schema', 'public')
        
        # Construct qualified table name
        qualified_table_name = f"{table_name}_{user_id}"[:63]
        
        # Connect to database
        engine = create_engine(db_url)
        inspector = inspect(engine)
        
        # Check if table exists
        if qualified_table_name not in inspector.get_table_names(schema=schema):
            return {"exists": False}
        
        # Get column information
        columns = inspector.get_columns(qualified_table_name, schema=schema)
        
        # Get row count
        with engine.connect() as conn:
            result = conn.execute(text(f'SELECT COUNT(*) FROM "{schema}"."{qualified_table_name}"'))
            row_count = result.scalar()
        
        return {
            "exists": True,
            "qualified_name": qualified_table_name,
            "columns": [col['name'] for col in columns],
            "column_types": {col['name']: str(col['type']) for col in columns},
            "row_count": row_count
        }
        
    except Exception as e:
        return {
            "exists": False,
            "error": str(e)
        }
