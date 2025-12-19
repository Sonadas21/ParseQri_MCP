import os
import shutil
import sqlalchemy
from sqlalchemy import inspect, create_engine, text
from pathlib import Path
import argparse
import time
import psutil

def clear_postgres_tables(user_id=None, db_url="postgresql://postgres:password@localhost:5432/parseqri", schema="public"):
    """
    Clear PostgreSQL tables for a specific user or all users.
    
    Args:
        user_id: Optional user ID to limit deletion to a specific user's tables
        db_url: PostgreSQL connection URL
        schema: Database schema name
    """
    # Define system tables that should be protected
    protected_tables = ["users", "user_databases", "system_config", "migrations"]
    
    try:
        # Create SQLAlchemy engine
        engine = create_engine(db_url)
        print(f"PostgreSQL connection established successfully")
        
        with engine.connect() as conn:
            inspector = inspect(engine)
            all_tables = inspector.get_table_names(schema=schema)
            
            # Filter tables based on user_id and protected tables
            if user_id:
                # Only drop tables with specific user prefix
                tables_to_drop = [table for table in all_tables if table.startswith(f"{user_id}_")]
                print(f"Found {len(tables_to_drop)} tables for user {user_id}")
            else:
                # Drop all user tables but protect system tables
                tables_to_drop = []
                for table in all_tables:
                    # Skip protected tables
                    if table in protected_tables:
                        print(f"Skipping protected table: {table}")
                        continue
                        
                    # Check if the table follows the user_id_name pattern
                    parts = table.split('_', 1)
                    if len(parts) > 1 and parts[0].isdigit():
                        tables_to_drop.append(table)
                    elif table != "users" and table != "user_databases":
                        # Also include other tables that don't match the pattern
                        # but aren't system tables
                        tables_to_drop.append(table)
                
                print(f"Found {len(tables_to_drop)} user-related tables to drop")
            
            # Drop each table
            for table in tables_to_drop:
                try:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                    print(f"Dropped table: {table}")
                except Exception as e:
                    print(f"Error dropping table {table}: {e}")
            
            # Commit the transaction
            conn.commit()
            
        return True
    except Exception as e:
        print(f"Error clearing PostgreSQL tables: {e}")
        return False

def clear_chromadb_data(user_id=None, db_storage_dir="../data/db_storage", max_retries=3, retry_delay=1):
    """
    Clear ChromaDB collections for a specific user or all users.
    
    Args:
        user_id: Optional user ID to limit deletion to a specific user's collections
        db_storage_dir: Directory path where ChromaDB data is stored
        max_retries: Maximum number of retries for locked files
        retry_delay: Delay between retries in seconds
    """
    try:
        storage_path = Path(db_storage_dir)
        
        if not storage_path.exists():
            print(f"ChromaDB storage directory not found: {storage_path}")
            return True  # Nothing to delete

        def remove_directory(dir_path, retries=0):
            try:
                if dir_path.exists():
                    # Check for locked files like SQLite databases
                    for file in dir_path.glob("**/*.sqlite3"):
                        if file.exists():
                            try:
                                # Try to open the file to check if it's locked
                                with open(file, 'a'):
                                    pass
                            except PermissionError:
                                print(f"File {file} is locked. Attempting to close any open handles...")
                                # Try to identify processes using the file (Windows-specific)
                                for proc in psutil.process_iter(['pid', 'name', 'open_files']):
                                    try:
                                        for open_file in proc.open_files() or []:
                                            if str(file) in open_file.path:
                                                print(f"Process {proc.name()} (PID: {proc.pid}) is using the file")
                                                # You could optionally terminate the process, but this is risky
                                                # proc.terminate()
                                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                                        pass
                    
                    # Try to remove the directory
                    shutil.rmtree(dir_path)
                    print(f"Removed ChromaDB data for: {dir_path.name}")
                    return True
            except (PermissionError, OSError) as e:
                if retries < max_retries:
                    print(f"Error removing {dir_path}: {e}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    return remove_directory(dir_path, retries + 1)
                else:
                    print(f"Failed to remove {dir_path} after {max_retries} attempts: {e}")
                    # Try alternative deletion method
                    try:
                        os.system(f'rd /s /q "{dir_path}"')
                        if not dir_path.exists():
                            print(f"Successfully removed {dir_path} using system command")
                            return True
                    except Exception as alt_e:
                        print(f"Alternative removal method also failed: {alt_e}")
                    return False
            return False
        
        if user_id:
            # Delete specific user directory
            user_dir = storage_path / str(user_id)
            if user_dir.exists():
                success = remove_directory(user_dir)
                if not success:
                    print(f"Could not completely remove ChromaDB data for user: {user_id}")
                    return False
            else:
                print(f"No ChromaDB data found for user: {user_id}")
        else:
            # Delete all user directories
            user_count = 0
            failed_count = 0
            for item in storage_path.iterdir():
                if item.is_dir():
                    success = remove_directory(item)
                    if success:
                        user_count += 1
                    else:
                        failed_count += 1
            
            print(f"Removed ChromaDB data for {user_count} users, failed for {failed_count} users")
            if failed_count > 0:
                return False
        
        return True
    except Exception as e:
        print(f"Error clearing ChromaDB data: {e}")
        return False

def main():
    """Main function to handle database clearing operations"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Clear ParseQri database data")
    parser.add_argument('--user', '-u', type=str, help='User ID to clear data for (omit to clear all users)')
    parser.add_argument('--postgres-only', action='store_true', help='Clear only PostgreSQL data')
    parser.add_argument('--chromadb-only', action='store_true', help='Clear only ChromaDB data')
    parser.add_argument('--db-url', type=str, default="postgresql://postgres:password@localhost:5432/parseqri", 
                      help='PostgreSQL database URL')
    parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    # Determine which databases to clear
    clear_postgres = not args.chromadb_only
    clear_chroma = not args.postgres_only
    
    # Show summary of operations
    if args.user:
        print(f"Clearing database data for user: {args.user}")
    else:
        print("Clearing database data for ALL users")
    
    print(f"Operations: PostgreSQL={clear_postgres}, ChromaDB={clear_chroma}")
    
    # Confirmation prompt
    if not args.force:
        confirmation = input("Are you sure you want to proceed? This action cannot be undone. (y/n): ")
        if confirmation.lower() != 'y':
            print("Operation cancelled.")
            return
    
    # Clear PostgreSQL tables
    if clear_postgres:
        print("\n--- Clearing PostgreSQL tables ---")
        success = clear_postgres_tables(args.user, args.db_url)
        if success:
            print("PostgreSQL tables cleared successfully.")
        else:
            print("Failed to clear PostgreSQL tables.")
    
    # Clear ChromaDB data
    if clear_chroma:
        print("\n--- Clearing ChromaDB data ---")
        success = clear_chromadb_data(args.user)
        if success:
            print("ChromaDB data cleared successfully.")
        else:
            print("Failed to clear ChromaDB data.")
    
    print("\nDatabase clearing operations completed.")

if __name__ == "__main__":
    main() 