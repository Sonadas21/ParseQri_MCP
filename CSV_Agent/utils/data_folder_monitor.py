import os
import time
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List
from utils.csv_retriever import CSVRetriever

class DataFolderMonitor:
    """
    Utility to monitor a data folder for CSV files and automatically process them.
    This class watches for new CSV files in a designated folder and loads them into
    the configured SQLite database.
    """
    
    def __init__(self, 
                 data_folder: str = "data",
                 db_name: str = "loan_db.db", 
                 table_name: str = "loan_dt",
                 auto_create_folder: bool = True):
        """
        Initialize the data folder monitor.
        
        Args:
            data_folder: Path to the folder to monitor for CSV files
            db_name: Name of the database to load data into
            table_name: Default table name to use
            auto_create_folder: Whether to create the data folder if it doesn't exist
        """
        self.data_folder = Path(data_folder)
        self.db_name = db_name
        self.table_name = table_name
        self.csv_retriever = CSVRetriever()
        self.processed_files = set()
        
        # Create the data folder if it doesn't exist and auto_create_folder is True
        if auto_create_folder and not self.data_folder.exists():
            self.data_folder.mkdir(parents=True)
            print(f"Created data folder: {self.data_folder}")
    
    def get_unprocessed_files(self) -> List[Path]:
        """
        Get a list of unprocessed CSV files in the data folder.
        
        Returns:
            List of paths to unprocessed CSV files
        """
        if not self.data_folder.exists():
            return []
            
        csv_files = [f for f in self.data_folder.glob("*.csv") if f.is_file()]
        return [f for f in csv_files if str(f) not in self.processed_files]
    
    def process_file(self, file_path: Path) -> bool:
        """
        Process a single CSV file by loading it into the database.
        
        Args:
            file_path: Path to the CSV file to process
            
        Returns:
            True if processing was successful, False otherwise
        """
        if not file_path.exists():
            print(f"File does not exist: {file_path}")
            return False
            
        # Extract table name from filename if not specified
        table_name = self.table_name
        if table_name == "loan_dt" and "loan" not in file_path.stem.lower():
            # Use the filename as table name if default is being used and doesn't match
            table_name = file_path.stem.lower().replace(" ", "_")
        
        # Load the file into the database
        success, message = self.csv_retriever.load_to_sqlite(
            str(file_path),
            self.db_name,
            table_name=table_name,
            clean_names=True,
            if_exists="replace"
        )
        
        if success:
            self.processed_files.add(str(file_path))
            print(f"Successfully processed {file_path}: {message}")
        else:
            print(f"Failed to process {file_path}: {message}")
            
        return success
    
    def process_all_files(self) -> Dict[str, bool]:
        """
        Process all unprocessed CSV files in the data folder.
        
        Returns:
            Dictionary mapping file paths to processing success status
        """
        unprocessed_files = self.get_unprocessed_files()
        if not unprocessed_files:
            print(f"No unprocessed CSV files found in {self.data_folder}")
            return {}
            
        results = {}
        for file_path in unprocessed_files:
            results[str(file_path)] = self.process_file(file_path)
            
        return results
    
    def watch_folder(self, interval: int = 5, max_iterations: Optional[int] = None):
        """
        Watch the data folder for new CSV files and process them.
        
        Args:
            interval: Number of seconds to wait between checks
            max_iterations: Maximum number of iterations (None for infinite)
        """
        print(f"Watching folder {self.data_folder} for CSV files...")
        iteration = 0
        
        try:
            while max_iterations is None or iteration < max_iterations:
                self.process_all_files()
                time.sleep(interval)
                iteration += 1
        except KeyboardInterrupt:
            print("Folder watching stopped by user.")
            
    def get_db_schema(self) -> Dict[str, Dict[str, str]]:
        """
        Get the schema of all tables in the database.
        
        Returns:
            Dictionary mapping table names to their schemas
        """
        tables = self.csv_retriever.list_tables(self.db_name)
        schema = {}
        
        for table in tables:
            schema[table] = self.csv_retriever.get_schema(self.db_name, table)
            
        return schema 