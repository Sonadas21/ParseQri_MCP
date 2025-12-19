import os
import pandas as pd
import sqlite3
from typing import List, Dict, Optional, Tuple
from pathlib import Path

class CSVRetriever:
    """
    Utility for finding, loading and retrieving data from CSV files and loading into databases.
    Provides functionality to scan directories for CSV files and load them into SQLite.
    """
    
    def __init__(self, base_dir: str = None):
        """
        Initialize the CSV Retriever.
        
        Args:
            base_dir: Optional base directory to scan for CSV files
        """
        self.base_dir = base_dir or os.getcwd()
        self.csv_files = {}  # Maps CSV paths to metadata
        self.current_db = None
        self.db_table_map = {}  # Maps database paths to tables they contain
        
    def scan_directory(self, directory: str = None, recursive: bool = True) -> Dict[str, Dict]:
        """
        Scan a directory for CSV files and collect metadata.
        
        Args:
            directory: Directory to scan (defaults to base_dir)
            recursive: Whether to scan subdirectories
            
        Returns:
            Dictionary mapping file paths to metadata
        """
        directory = directory or self.base_dir
        csv_files = {}
        
        # Walk through the directory
        for root, _, files in os.walk(directory):
            # Skip if not recursive and not the root directory
            if not recursive and root != directory:
                continue
                
            for file in files:
                if file.lower().endswith('.csv'):
                    path = os.path.join(root, file)
                    csv_files[path] = self._get_csv_metadata(path)
                    
        self.csv_files.update(csv_files)
        return csv_files
    
    def _get_csv_metadata(self, filepath: str) -> Dict:
        """
        Get metadata for a CSV file (sampling first few rows).
        
        Args:
            filepath: Path to the CSV file
            
        Returns:
            Dictionary with metadata about the CSV
        """
        try:
            # Read just the first few rows for metadata
            df_sample = pd.read_csv(filepath, nrows=5)
            
            return {
                'filename': os.path.basename(filepath),
                'columns': df_sample.columns.tolist(),
                'row_count_sample': len(df_sample),
                'size_bytes': os.path.getsize(filepath),
                'last_modified': os.path.getmtime(filepath)
            }
        except Exception as e:
            return {
                'filename': os.path.basename(filepath),
                'error': str(e)
            }
    
    def load_csv(self, filepath: str, **pd_kwargs) -> Optional[pd.DataFrame]:
        """
        Load a CSV file into a pandas DataFrame.
        
        Args:
            filepath: Path to the CSV file
            pd_kwargs: Additional arguments to pass to pandas.read_csv
            
        Returns:
            DataFrame containing the CSV data
        """
        try:
            df = pd.read_csv(filepath, **pd_kwargs)
            
            # Update metadata with full count
            if filepath in self.csv_files:
                self.csv_files[filepath]['row_count'] = len(df)
                
            return df
        except Exception as e:
            print(f"Error loading CSV {filepath}: {e}")
            return None
    
    def clean_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean column names in a DataFrame for database compatibility.
        
        Args:
            df: DataFrame to clean
            
        Returns:
            DataFrame with cleaned column names
        """
        def clean_name(name):
            # Convert to lowercase
            name = str(name).lower()
            # Replace problematic characters
            name = name.replace(' ', '_').replace('\n', '_').replace('-', '_')
            name = name.replace('/', '_').replace('\\', '_').replace('(', '').replace(')', '')
            name = name.replace(',', '').replace('.', '_').replace(':', '_')
            # Ensure name starts with a letter or underscore
            if name and not (name[0].isalpha() or name[0] == '_'):
                name = 'col_' + name
            return name
            
        df.columns = [clean_name(col) for col in df.columns]
        return df
    
    def load_to_sqlite(self, csv_path: str, db_path: str, table_name: str = None,
                      if_exists: str = 'replace', clean_names: bool = True, 
                      **pd_kwargs) -> Tuple[bool, str]:
        """
        Load a CSV file into an SQLite database.
        
        Args:
            csv_path: Path to the CSV file
            db_path: Path to the SQLite database
            table_name: Name for the table (defaults to CSV filename without extension)
            if_exists: What to do if table exists ('fail', 'replace', 'append')
            clean_names: Whether to clean column names
            pd_kwargs: Additional arguments to pass to pandas.read_csv
            
        Returns:
            Tuple of (success boolean, message string)
        """
        try:
            # Default table name to filename without extension
            if table_name is None:
                table_name = os.path.splitext(os.path.basename(csv_path))[0]
                
            # Load the CSV
            df = self.load_csv(csv_path, **pd_kwargs)
            if df is None:
                return False, f"Failed to load CSV file: {csv_path}"
                
            # Clean column names if requested
            if clean_names:
                df = self.clean_column_names(df)
                
            # Create or connect to the database
            with sqlite3.connect(db_path) as conn:
                # Write to the database
                df.to_sql(table_name, conn, if_exists=if_exists, index=False)
                
                # Update our database-table mapping
                if db_path not in self.db_table_map:
                    self.db_table_map[db_path] = []
                if table_name not in self.db_table_map[db_path]:
                    self.db_table_map[db_path].append(table_name)
                
                self.current_db = db_path
                
                return True, f"Successfully loaded {len(df)} rows into {db_path}, table {table_name}"
                
        except Exception as e:
            return False, f"Error loading CSV to SQLite: {str(e)}"
    
    def get_schema(self, db_path: str, table_name: str) -> Dict[str, str]:
        """
        Get the schema for a table in an SQLite database.
        
        Args:
            db_path: Path to the SQLite database
            table_name: Name of the table
            
        Returns:
            Dictionary mapping column names to types
        """
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table_name})")
                schema_info = cursor.fetchall()
                
                # Column 1 is name, column 2 is type
                schema = {col[1]: col[2] for col in schema_info}
                return schema
        except Exception as e:
            print(f"Error retrieving schema: {e}")
            return {}
    
    def list_tables(self, db_path: str) -> List[str]:
        """
        List all tables in an SQLite database.
        
        Args:
            db_path: Path to the SQLite database
            
        Returns:
            List of table names
        """
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                return [table[0] for table in tables]
        except Exception as e:
            print(f"Error listing tables: {e}")
            return []
    
    def preview_table(self, db_path: str, table_name: str, limit: int = 5) -> Optional[pd.DataFrame]:
        """
        Preview rows from a table in an SQLite database.
        
        Args:
            db_path: Path to the SQLite database
            table_name: Name of the table
            limit: Maximum number of rows to retrieve
            
        Returns:
            DataFrame containing preview data
        """
        try:
            with sqlite3.connect(db_path) as conn:
                query = f"SELECT * FROM {table_name} LIMIT {limit}"
                df = pd.read_sql_query(query, conn)
                return df
        except Exception as e:
            print(f"Error previewing table: {e}")
            return None
    
    def get_csv_stats(self, csv_path: str = None) -> Dict:
        """
        Get detailed statistics about a CSV file.
        
        Args:
            csv_path: Path to the CSV file (None to get stats for all)
            
        Returns:
            Dictionary with statistics
        """
        if csv_path is None:
            # Return stats for all CSV files
            return {
                'total_files': len(self.csv_files),
                'files': self.csv_files
            }
        
        if csv_path not in self.csv_files:
            # If we don't have metadata yet, try to load it
            self.csv_files[csv_path] = self._get_csv_metadata(csv_path)
            
        # Try to get row count if not already known
        if 'row_count' not in self.csv_files[csv_path]:
            try:
                # Efficiently count lines without loading the whole file
                with open(csv_path, 'r') as f:
                    # Subtract 1 for header
                    self.csv_files[csv_path]['row_count'] = sum(1 for line in f) - 1
            except Exception:
                pass
                
        return self.csv_files[csv_path] 