# CSVRetriever

The `CSVRetriever` class is a utility for working with CSV files in the TextToSQL Agent system. It provides functionality to load CSV files into SQLite databases, which can then be queried using SQL.

## Features

- Scan directories for CSV files
- Get statistics about CSV files (columns, row count)
- Load CSV files into pandas DataFrames
- Load CSV files into SQLite databases with customizable table names
- List tables in a database
- Get schema information for database tables
- Preview data from database tables

## Usage

### Basic Usage

```python
from utils import CSVRetriever

# Initialize the retriever
retriever = CSVRetriever()

# Scan a directory for CSV files
retriever.scan_directory("path/to/csv/files")

# Get information about the CSV files
csv_stats = retriever.get_csv_stats()
for file_path, stats in csv_stats.items():
    print(f"File: {file_path}")
    print(f"Columns: {stats['columns']}")
    print(f"Row count: {stats['row_count']}")

# Load a CSV file into an SQLite database
retriever.load_to_sqlite(
    "path/to/file.csv", 
    "path/to/database.db",
    table_name="my_table",
    clean_names=True,
    if_exists="replace"
)

# List tables in the database
tables = retriever.list_tables("path/to/database.db")
print(f"Tables: {tables}")

# Get schema for a table
schema = retriever.get_schema("path/to/database.db", "my_table")
for column_info in schema:
    print(column_info)

# Preview data from a table
preview = retriever.preview_table("path/to/database.db", "my_table", limit=5)
print(preview)
```

### Parameters

#### `load_to_sqlite` method

- `csv_path` (str): Path to the CSV file to load
- `db_path` (str): Path to the SQLite database file
- `table_name` (str, optional): Name of the table to create. If None, the filename without extension is used.
- `clean_names` (bool, optional): Whether to clean column names to be SQL-friendly. Default is True.
- `if_exists` (str, optional): How to behave if the table already exists:
  - 'fail': Raise an error (default)
  - 'replace': Drop the table before inserting new values
  - 'append': Insert new values to the existing table

## Example

See the test script at `tests/test_csv_retriever.py` for a complete example of how to use the CSVRetriever class. 