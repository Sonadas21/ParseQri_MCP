"""
Test script for the CSVRetriever utility.
This demonstrates how to use the CSVRetriever to load CSV files into a database.
"""
import os
import sqlite3
from pathlib import Path
import pandas as pd

# Import the CSVRetriever from the utils package
from utils.csv_retriever import CSVRetriever

def main():
    # Create a test directory with a sample CSV file if it doesn't exist
    test_dir = Path("test_data")
    test_dir.mkdir(exist_ok=True)
    
    # Create a sample CSV file for testing
    sample_data = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
        "age": [25, 30, 35, 40, 45],
        "city": ["New York", "London", "Paris", "Tokyo", "Sydney"]
    })
    
    sample_file = test_dir / "sample.csv"
    sample_data.to_csv(sample_file, index=False)
    
    # Create another sample CSV file with different schema
    other_data = pd.DataFrame({
        "product_id": [101, 102, 103],
        "product_name": ["Laptop", "Phone", "Tablet"],
        "price": [1200.50, 800.75, 350.25],
        "in_stock": [True, False, True]
    })
    
    other_file = test_dir / "products.csv"
    other_data.to_csv(other_file, index=False)
    
    # Initialize the CSVRetriever
    db_path = "test_data/test.db"
    retriever = CSVRetriever()
    
    # Scan the directory for CSV files
    print("Scanning directory for CSV files...")
    retriever.scan_directory(str(test_dir))
    
    # Show the found CSV files
    print("\nFound CSV files:")
    csv_stats = retriever.get_csv_stats()
    for file_path, stats in csv_stats.items():
        print(f"- {file_path}")
        print(f"  Columns: {', '.join(stats['columns'])}")
        print(f"  Rows: {stats['row_count']}")
    
    # Load a CSV file into a pandas DataFrame
    print("\nLoading sample.csv into DataFrame...")
    df = retriever.load_csv(str(sample_file))
    print(df.head())
    
    # Load a CSV file into SQLite database
    print("\nLoading sample.csv into SQLite database...")
    retriever.load_to_sqlite(str(sample_file), db_path, table_name="people", 
                            clean_names=True, if_exists="replace")
    
    # Load another CSV file into the same database
    print("\nLoading products.csv into SQLite database...")
    retriever.load_to_sqlite(str(other_file), db_path, table_name="products",
                            clean_names=True, if_exists="replace")
    
    # List all tables in the database
    print("\nTables in the database:")
    tables = retriever.list_tables(db_path)
    print(tables)
    
    # Get schema for a table
    print("\nSchema for 'people' table:")
    schema = retriever.get_schema(db_path, "people")
    for column_info in schema:
        print(f"- {column_info}")
    
    # Preview data from a table
    print("\nPreview of 'people' table:")
    preview = retriever.preview_table(db_path, "people", limit=3)
    print(preview)
    
    print("\nPreview of 'products' table:")
    preview = retriever.preview_table(db_path, "products", limit=3)
    print(preview)
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main() 