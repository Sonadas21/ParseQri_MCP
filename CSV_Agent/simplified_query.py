#!/usr/bin/env python3
"""
Simplified query script for the integrated PDF/Image to SQL system.
This script doesn't rely on LLMs for query processing.
"""
import os
import sys
import sqlite3
import subprocess
import pandas as pd
from pathlib import Path

# Define paths
ROOT_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent
DATA_DIR = ROOT_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
CSV_OUTPUT_DIR = DATA_DIR / "csv_output"
DB_STORAGE_DIR = DATA_DIR / "db_storage"
CONVERSION_TOOL_DIR = ROOT_DIR / "conversion_tool"

# Default database settings
DEFAULT_DB_NAME = "query_data.db"
DEFAULT_TABLE_NAME = "extracted_data"

def process_input_files():
    """Process PDF/image files in the input directory"""
    # Check if there are files to process
    pdf_files = list(INPUT_DIR.glob("*.pdf"))
    image_files = []
    for ext in ["*.png", "*.jpg", "*.jpeg", "*.tiff", "*.bmp"]:
        image_files.extend(list(INPUT_DIR.glob(ext)))
    
    # Check for CSV files (for direct ingestion)
    csv_files = list(INPUT_DIR.glob("*.csv"))
    
    if not (pdf_files or image_files or csv_files):
        print("No PDF, image, or CSV files found in input directory.")
        return False
    
    print(f"Found {len(pdf_files)} PDF files, {len(image_files)} image files, and {len(csv_files)} CSV files.")
    
    # Step 1: Ensure directories exist
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DB_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    (CONVERSION_TOOL_DIR / "pdfs").mkdir(exist_ok=True)
    
    # Handle PDF/image files through conversion_tool
    if pdf_files or image_files:
        # Step 2: Copy files to conversion_tool/pdfs
        print("\nStep 1: Copying files to conversion tool...")
        for pdf_file in pdf_files:
            target_path = CONVERSION_TOOL_DIR / "pdfs" / pdf_file.name
            with open(pdf_file, 'rb') as src, open(target_path, 'wb') as dst:
                dst.write(src.read())
            print(f"Copied {pdf_file.name} to conversion tool")
        
        for img_file in image_files:
            target_path = CONVERSION_TOOL_DIR / "pdfs" / img_file.name
            with open(img_file, 'rb') as src, open(target_path, 'wb') as dst:
                dst.write(src.read())
            print(f"Copied {img_file.name} to conversion tool")
        
        # Step 3: Run the conversion tool
        print("\nStep 2: Converting files to CSV...")
        python_executable = sys.executable
        
        conversion_result = subprocess.run(
            [python_executable, "main.py"],
            cwd=str(CONVERSION_TOOL_DIR),
            capture_output=True,
            text=True
        )
        
        if conversion_result.returncode != 0:
            print("Error running conversion tool:")
            print(conversion_result.stderr)
            return False
        
        print("Conversion completed successfully")
        
        # Step 4: Copy CSV files to output directory
        print("\nStep 3: Copying CSV files to output directory...")
        conversion_csv_files = list((CONVERSION_TOOL_DIR / "csv_output").glob("*.csv"))
        
        for csv_file in conversion_csv_files:
            target_path = CSV_OUTPUT_DIR / csv_file.name
            with open(csv_file, 'rb') as src, open(target_path, 'wb') as dst:
                dst.write(src.read())
            print(f"Copied {csv_file.name} to output directory")
    
    # Handle direct CSV files
    if csv_files:
        print("\nStep 4: Copying direct CSV files to output directory...")
        for csv_file in csv_files:
            target_path = CSV_OUTPUT_DIR / csv_file.name
            with open(csv_file, 'rb') as src, open(target_path, 'wb') as dst:
                dst.write(src.read())
            print(f"Copied {csv_file.name} to output directory")
    
    return True

def ingest_csv_to_database():
    """Ingest CSV files to SQLite database"""
    print("\nStep 4: Ingesting CSV files to database...")
    db_path = DB_STORAGE_DIR / DEFAULT_DB_NAME
    
    csv_files = list(CSV_OUTPUT_DIR.glob("*.csv"))
    if not csv_files:
        print("No CSV files found in output directory.")
        return False
    
    try:
        for csv_file in csv_files:
            table_name = csv_file.stem
            print(f"Processing {csv_file.name}...")
            
            # Read CSV file
            df = pd.read_csv(csv_file)
            
            # Clean column names
            df.columns = [col.lower().replace(' ', '_').replace('\n', '_').replace('/', '_')
                          .replace(',', '').replace('(', '').replace(')', '')
                          for col in df.columns]
            
            # Save to database
            with sqlite3.connect(str(db_path)) as conn:
                df.to_sql(table_name, conn, if_exists='replace', index=False)
                
            print(f"Successfully loaded {len(df)} rows into {db_path}, table {table_name}")
        
        return True
    
    except Exception as e:
        print(f"Error ingesting CSV files: {str(e)}")
        return False

def show_database_info():
    """Show information about the database"""
    db_path = DB_STORAGE_DIR / DEFAULT_DB_NAME
    
    if not db_path.exists():
        print(f"Database file not found: {db_path}")
        return
    
    try:
        with sqlite3.connect(str(db_path)) as conn:
            # Get list of tables
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            print("\nDatabase Information:")
            print(f"Database: {db_path.name}")
            print(f"Tables: {', '.join(tables)}")
            
            # Show schema for each table
            for table in tables:
                print(f"\nTable: {table}")
                
                # Get schema
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                print("Schema:")
                for col in columns:
                    print(f"  - {col[1]} ({col[2]})")
                
                # Show sample data
                cursor.execute(f"SELECT * FROM {table} LIMIT 5")
                rows = cursor.fetchall()
                
                if rows:
                    print("\nSample Data:")
                    for row in rows:
                        print(f"  {row}")
                else:
                    print("\nNo data in table")
    
    except Exception as e:
        print(f"Error reading database: {str(e)}")

def execute_query(query):
    """Execute an SQL query directly"""
    db_path = DB_STORAGE_DIR / DEFAULT_DB_NAME
    
    if not db_path.exists():
        print(f"Database file not found: {db_path}")
        return
    
    try:
        with sqlite3.connect(str(db_path)) as conn:
            result = pd.read_sql_query(query, conn)
            return result
    
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        return None

def main():
    """Main function"""
    # Create directories if they don't exist
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DB_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check if we have arguments
    if len(sys.argv) < 2:
        print("No arguments provided.")
        print("Usage:")
        print("  python simplified_query.py process   # Process files in input directory")
        print("  python simplified_query.py info      # Show database information")
        print("  python simplified_query.py 'SQL'     # Execute SQL query")
        return
    
    command = sys.argv[1]
    
    if command.lower() == 'process':
        # Process files, ingest to database, and show info
        if process_input_files():
            ingest_csv_to_database()
        show_database_info()
    
    elif command.lower() == 'info':
        # Show database information
        show_database_info()
    
    else:
        # Assume it's an SQL query
        result = execute_query(command)
        
        if result is not None:
            print("\nQuery Result:")
            print(result)

if __name__ == "__main__":
    main() 