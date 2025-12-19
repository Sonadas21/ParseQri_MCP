import sys
import os
import json
import subprocess
import argparse
from pathlib import Path
import time
from core.orchestrator import TextSQLOrchestrator
from utils.data_folder_monitor import DataFolderMonitor
import sqlalchemy
from sqlalchemy import inspect, create_engine, text

def get_available_users():
    """Get available user IDs from storage directory"""
    storage_dir = Path("../data/db_storage")
    if not storage_dir.exists():
        return ["default_user"]
    
    users = []
    for item in storage_dir.iterdir():
        if item.is_dir():
            users.append(item.name)
    
    return users if users else ["default_user"]

def get_postgres_tables(user_id=None):
    """Get available tables directly from PostgreSQL"""
    try:
        db_url = "postgresql://postgres:password@localhost:5432/parseqri"
        engine = create_engine(db_url)
        with engine.connect() as conn:
            inspector = inspect(engine)
            all_tables = inspector.get_table_names(schema='public')
            
            if user_id:
                # Filter tables for specific user
                tables = [table for table in all_tables if table.startswith(f"{user_id}_")]
            else:
                # Get all tables with user ID info
                tables = []
                user_tables = {}
                
                for table in all_tables:
                    parts = table.split("_", 1)
                    if len(parts) > 1:
                        user_id = parts[0]
                        table_name = parts[1]
                        if user_id not in user_tables:
                            user_tables[user_id] = []
                        user_tables[user_id].append(table_name)
                
                # Format table info
                for user, tables_list in user_tables.items():
                    for table in tables_list:
                        tables.append(f"{user}: {table}")
            
            return tables
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return []

def initialize_chromadb_collection(user_id, force=False):
    """Initialize ChromaDB collection for a user from PostgreSQL data"""
    try:
        # First check if there's already data for this user in ChromaDB
        collection_path = Path(f"../data/db_storage/{user_id}/{user_id}_metadata")
        if collection_path.exists() and not force:
            print(f"ChromaDB collection already exists for user {user_id}")
            return True
            
        # Get orchestrator with all agents
        config_path = "config.json"
        if not os.path.exists(config_path):
            create_default_config(config_path)
            
        orchestrator = TextSQLOrchestrator(config_path)
        
        # Get the metadata_indexer agent
        if 'metadata_indexer' not in orchestrator.agents:
            print("Metadata indexer agent not available")
            return False
            
        metadata_indexer = orchestrator.agents['metadata_indexer']
        
        # Get list of tables for this user
        postgres_tables = get_postgres_tables(user_id)
        if not postgres_tables:
            print(f"No PostgreSQL tables found for user {user_id}")
            return False
            
        # For each table, create a metadata entry
        for full_table_name in postgres_tables:
            # Get table name without user prefix
            table_name = full_table_name[len(f"{user_id}_"):]
            
            # Create minimal metadata document
            print(f"Creating metadata entry for table: {table_name}")
            metadata_indexer.save_metadata_to_chroma(
                user_id=user_id,
                table_name=table_name,
                columns={"table": "PostgreSQL table"}  # Placeholder for columns
            )
            
        print(f"Successfully initialized ChromaDB collection for user {user_id}")
        return True
        
    except Exception as e:
        print(f"Error initializing ChromaDB collection: {e}")
        return False

def main():
    """Main entry point for the integrated PDF/Image to SQL query system"""
    # Get available users
    available_users = get_available_users()
    default_user = available_users[0] if available_users else "default_user"
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ParseQri Text-to-SQL Agent")
    parser.add_argument('query', nargs='?', help='Natural language query to process')
    parser.add_argument('--user', '-u', type=str, default=default_user, 
                      help=f'User ID for multi-user support (available: {", ".join(available_users)})')
    parser.add_argument('--upload', type=str, help='Path to CSV file to upload')
    parser.add_argument('--table', type=str, help='Suggested table name for CSV upload')
    parser.add_argument('--viz', '--visualization', action='store_true', help='Force visualization mode')
    parser.add_argument('--list-tables', action='store_true', help='List available tables for the user')
    parser.add_argument('--list-all-tables', action='store_true', help='List all tables in the database')
    parser.add_argument('--init-chromadb', action='store_true', help='Initialize ChromaDB collection for user')
    parser.add_argument('--db-id', type=int, help='Database ID for API integration')
    
    args = parser.parse_args()
    
    # Validate user ID
    current_user = args.user
    if current_user not in available_users:
        print(f"Warning: User '{current_user}' not found. Available users: {', '.join(available_users)}")
        print(f"Using '{default_user}' instead.")
        current_user = default_user
    
    print(f"Current user: {current_user}")
    
    # Load configuration
    config_path = "config.json"
    if not os.path.exists(config_path):
        create_default_config(config_path)
    
    # Load the configuration
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Initialize the orchestrator
    orchestrator = TextSQLOrchestrator(config_path)
    
    # Handle the init-chromadb command
    if args.init_chromadb:
        initialize_chromadb_collection(current_user, force=True)
        return
    
    # Handle the list-all-tables command
    if args.list_all_tables:
        all_tables = get_postgres_tables()
        
        if all_tables:
            print("\nAll tables in PostgreSQL (user: table):")
            for table in all_tables:
                print(f"  - {table}")
        else:
            print("  No PostgreSQL tables found")
            
        return
    
    # Handle the list-tables command
    if args.list_tables:
        # Direct access to the postgres_handler and metadata_indexer agents
        if 'postgres_handler' in orchestrator.agents and 'metadata_indexer' in orchestrator.agents:
            postgres_handler = orchestrator.agents['postgres_handler']
            metadata_indexer = orchestrator.agents['metadata_indexer']
            
            # Get tables from PostgreSQL
            tables = postgres_handler.list_user_tables(current_user)
            
            # Get tables from ChromaDB
            try:
                metadata_tables = metadata_indexer.list_user_tables(current_user)
            except Exception as e:
                print(f"Warning: Unable to get tables from ChromaDB: {e}")
                metadata_tables = []
            
            print(f"\nTables available for user {current_user}:")
            if tables:
                print("\nPostgres Tables:")
                for table in tables:
                    # Show table name without user prefix for clarity
                    if table.startswith(f"{current_user}_"):
                        display_name = table[len(f"{current_user}_"):]
                    else:
                        display_name = table
                    print(f"  - {display_name} (full name: {table})")
            else:
                print("  No PostgreSQL tables found")
                
            if metadata_tables:
                print("\nMetadata Indexed Tables:")
                for table in metadata_tables:
                    print(f"  - {table['table_name']} ({table['column_count']} columns)")
            else:
                print("  No metadata indexed tables found")
                
            # If no ChromaDB metadata, offer to initialize it
            if tables and not metadata_tables:
                print("\nNo ChromaDB metadata found but PostgreSQL tables exist.")
                print("You can initialize the ChromaDB collection with:")
                print(f"  python main.py --init-chromadb --user {current_user}")
            
            return
    
    # Handle file upload
    if args.upload:
        print(f"Uploading file: {args.upload} for user: {current_user}")
        if not os.path.exists(args.upload):
            print(f"Error: File not found: {args.upload}")
            return
            
        print("File exists, proceeding with upload")
        
        # Process CSV upload
        table_name = args.table or Path(args.upload).stem
        print(f"Using table name: {table_name}")
        
        # Check if metadata_indexer is available
        if 'metadata_indexer' in orchestrator.agents:
            print("Metadata indexer agent is available")
            metadata_indexer = orchestrator.agents['metadata_indexer']
        else:
            print("WARNING: Metadata indexer agent is NOT available")
        
        context = orchestrator.process_upload(
            csv_file=args.upload,
            user_id=current_user,
            suggested_table_name=table_name,
            db_id=args.db_id
        )
        
        # Display results
        if hasattr(context, 'table_name') and context.table_name:
            print(f"\nSuccessfully uploaded data to table: {context.table_name}")
            print("You can now query this data with:")
            print(f"  python main.py \"your question about the data\" --user {current_user}")
        else:
            print("\nError uploading data. Check the logs for more information.")
            
        return
    
    # Check if PDF/image processing is needed
    pdf_processing_needed = check_for_pdfs_or_images()

    if pdf_processing_needed:
        print("Found new PDF or image files to process")
        # Step 1: Run the conversion tool to convert PDF/images to CSV
        print("\nStep 1: Converting PDF/images to CSV...")
        try:
            # Ensure the input directory exists in conversion_tool
            os.makedirs("../conversion_tool/pdfs", exist_ok=True)
            
            # Copy the files from data/input to conversion_tool/pdfs
            copy_input_files()
            
            # Get the current Python interpreter path
            python_executable = sys.executable
            print(f"Using Python interpreter: {python_executable}")
            
            # Run the conversion tool
            conversion_result = subprocess.run(
                [python_executable, "../conversion_tool/main.py"],
                cwd="../conversion_tool",
                capture_output=True, 
                text=True
            )
            
            if conversion_result.returncode != 0:
                print("Error running conversion tool:")
                print(conversion_result.stderr)
                return
                
            print("Conversion completed successfully")
            
            # Step 2: Copy the CSV output to our data directory
            print("\nStep 2: Copying CSV output to data directory...")
            os.makedirs("../data/csv_output", exist_ok=True)
            
            # Copy the CSV file from conversion_tool/csv_output to data/csv_output
            copy_csv_files()
            
        except Exception as e:
            print(f"Error during PDF/image conversion: {str(e)}")
            return
    
    # Step 3: If CSV files are present, process and ingest them 
    # This is now handled by the upload argument, but we keep this for backward compatibility
    if not args.query and not args.upload and not args.list_tables:
        print("\nNo query or upload operation provided.")
        print("You can:")
        print("- Run a query with: python main.py 'Your query' --user <user_id>")
        print("- Upload a CSV with: python main.py --upload path/to/file.csv --user <user_id>")
        print("- List tables with: python main.py --list-tables --user <user_id>")
        print("\nExiting...")
        return
    
    # Step 4: Process query if provided
    if args.query:
        user_question = args.query
        print(f"\nProcessing query: {user_question}")
        
        # Check for visualization flag
        force_visualization = args.viz
        
        # Get the user's database path - dynamically based on user ID
        user_db_path = f"../data/db_storage/{current_user}"
        
        # Check if ChromaDB needs initialization
        chroma_collection_path = Path(f"../data/db_storage/{current_user}/{current_user}_metadata")
        if not chroma_collection_path.exists():
            print(f"ChromaDB collection not found for user {current_user}, attempting to initialize...")
            initialize_chromadb_collection(current_user)
        
        # Process query with user_id
        context = orchestrator.process_query(
            user_question, 
            user_db_path if os.path.exists(user_db_path) else "", # Use empty string if path doesn't exist
            "",  # Table name will be determined by metadata lookup
            user_id=current_user,
            force_visualization=force_visualization
        )
        
        # Display results
        if context.needs_visualization:
            print("\nVisualization response:")
            if context.visualization_data and 'html_path' in context.visualization_data:
                html_path = context.visualization_data['html_path']
                
                # Create a clickable file:// URL for the terminal
                file_url = f"file:///{os.path.abspath(html_path).replace(os.sep, '/')}"
                
                print(f"\nVisualization saved. Click this link to view: {file_url}")
                print("The visualization should open automatically in your default browser.")
                print("If it doesn't open, please click on the link above.")
            else:
                print(f"Visualization data: {context.visualization_data}")
        else:
            print("\nSQL Query:")
            print(context.sql_query)
            print("\nResponse:")
            print(context.formatted_response)

def check_for_pdfs_or_images():
    """Check if there are PDF or image files in the input directory"""
    input_dir = Path("../data/input")
    
    if not input_dir.exists():
        return False
        
    pdf_files = list(input_dir.glob("*.pdf"))
    image_files = []
    for ext in ["*.png", "*.jpg", "*.jpeg", "*.tiff", "*.bmp"]:
        image_files.extend(list(input_dir.glob(ext)))
    
    return len(pdf_files) > 0 or len(image_files) > 0

def copy_input_files():
    """Copy files from data/input to conversion_tool/pdfs"""
    input_dir = Path("../data/input")
    output_dir = Path("../conversion_tool/pdfs")
    
    # Ensure output directory exists
    output_dir.mkdir(exist_ok=True)
    
    # Copy PDF files
    pdf_files = list(input_dir.glob("*.pdf"))
    for pdf_file in pdf_files:
        target_path = output_dir / pdf_file.name
        # Read and write file content
        with open(pdf_file, 'rb') as src, open(target_path, 'wb') as dst:
            dst.write(src.read())
        print(f"Copied {pdf_file.name} to conversion tool")
    
    # Copy image files
    image_extensions = ["*.png", "*.jpg", "*.jpeg", "*.tiff", "*.bmp"]
    for ext in image_extensions:
        image_files = list(input_dir.glob(ext))
        for img_file in image_files:
            target_path = output_dir / img_file.name
            # Read and write file content
            with open(img_file, 'rb') as src, open(target_path, 'wb') as dst:
                dst.write(src.read())
            print(f"Copied {img_file.name} to conversion tool")

def copy_csv_files():
    """Copy CSV files from conversion_tool/csv_output to data/csv_output"""
    conversion_output = Path("../conversion_tool/csv_output")
    data_dir = Path("../data/csv_output")
    
    # Ensure data directory exists
    data_dir.mkdir(exist_ok=True)
    
    # Copy all CSV files
    csv_files = list(conversion_output.glob("*.csv"))
    for csv_file in csv_files:
        target_path = data_dir / csv_file.name
        # Read and write file content
        with open(csv_file, 'rb') as src, open(target_path, 'wb') as dst:
            dst.write(src.read())
        print(f"Copied {csv_file.name} to data/csv_output")

def create_default_config(config_path):
    """Create a default configuration file if none exists"""
    default_config = {
        "agents": {
            "data_ingestion": {
                "module": "agents.data_ingestion",
                "class": "DataIngestionAgent",
                "params": {}
            },
            "schema_understanding": {
                "module": "agents.schema_understanding",
                "class": "SchemaUnderstandingAgent",
                "params": {
                    "llm_model": "mistral",
                    "api_base": "http://localhost:11434"
                }
            },
            "intent_classifier": {
                "module": "agents.intent_classification",
                "class": "IntentClassificationAgent",
                "params": {
                    "llm_model": "llama3.1",
                    "api_base": "http://localhost:11434"
                }
            },
            "sql_generation": {
                "module": "agents.sql_generation",
                "class": "SQLGenerationAgent",
                "params": {
                    "llm_model": "qwen2.5",
                    "api_base": "http://localhost:11434"
                }
            },
            "sql_validation": {
                "module": "agents.sql_validation",
                "class": "SQLValidationAgent",
                "params": {
                    "llm_model": "orca2",
                    "api_base": "http://localhost:11434"
                }
            },
            "query_execution": {
                "module": "agents.query_execution",
                "class": "QueryExecutionAgent",
                "params": {
                    "postgres_url": "postgresql://postgres:postgres@localhost:5432/parseqri_db"
                }
            },
            "response_formatting": {
                "module": "agents.response_formatting",
                "class": "ResponseFormattingAgent",
                "params": {
                    "llm_model": "mistral",
                    "api_base": "http://localhost:11434"
                }
            },
            "visualization": {
                "module": "agents.visualization",
                "class": "VisualizationAgent",
                "params": {
                    "llm_model": "llama3.1",
                    "api_base": "http://localhost:11434"
                }
            },
            "data_preprocessing": {
                "module": "agents.data_preprocessing",
                "class": "DataPreprocessingAgent",
                "params": {}
            },
            "query_cache": {
                "module": "agents.query_cache",
                "class": "QueryCacheAgent",
                "params": {
                    "cache_dir": "cache"
                }
            },
            "schema_management": {
                "module": "agents.schema_management",
                "class": "SchemaManagementAgent",
                "params": {}
            },
            "advanced_visualization": {
                "module": "agents.advanced_visualization",
                "class": "AdvancedVisualizationAgent",
                "params": {}
            },
            "metadata_indexer": {
                "module": "agents.metadata_indexer",
                "class": "MetadataIndexerAgent",
                "params": {
                    "llm_model": "llama3.1",
                    "api_base": "http://localhost:11434",
                    "chroma_persist_dir": "../data/db_storage"
                }
            },
            "postgres_handler": {
                "module": "agents.postgres_handler",
                "class": "PostgresHandlerAgent",
                "params": {
                    "db_url": "postgresql://postgres:password@localhost:5432/parseqri",
                    "schema": "public"
                }
            },
            "query_router": {
                "module": "agents.query_router",
                "class": "QueryRouterAgent",
                "params": {}
            }
        },
        "database": {
            "default_db_name": "",  # This will be determined dynamically
            "default_table_name": "",  # This will be determined dynamically
            "data_folder": "../data/input",  # Updated to use input folder directly
            "postgres": {
                "db_url": "postgres://postgres:password@localhost:5432/parseqri",
                "schema": "public"
            }
        },
        "logging": {
            "level": "INFO",
            "file": "../data/query_logs/textsql.log"
        }
    }
    
    with open(config_path, 'w') as f:
        json.dump(default_config, f, indent=2)
    
    print(f"Created default configuration file: {config_path}")

if __name__ == "__main__":
    main() 