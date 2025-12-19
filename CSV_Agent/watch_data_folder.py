#!/usr/bin/env python3
"""
Script to continuously monitor the data folder for new CSV files.
Run this script in a separate terminal window to automatically process
CSV files as they are added to the data folder.
"""
import os
import sys
import json
import argparse
from utils.data_folder_monitor import DataFolderMonitor

def main():
    """Main entry point for the data folder monitor script."""
    parser = argparse.ArgumentParser(description='Monitor a folder for CSV files and load them into a database.')
    parser.add_argument('--data-folder', type=str, default=None, 
                        help='Path to the data folder (default: use config.json)')
    parser.add_argument('--db-name', type=str, default=None,
                        help='Name of the database (default: use config.json)')
    parser.add_argument('--table-name', type=str, default=None,
                        help='Default table name for CSV files (default: use config.json)')
    parser.add_argument('--interval', type=int, default=5,
                        help='Time interval between checks in seconds (default: 5)')
    args = parser.parse_args()
    
    # Load configuration
    config_path = "config.json"
    if not os.path.exists(config_path):
        print(f"Error: Configuration file {config_path} not found.")
        print("Please run main.py first to create a default configuration.")
        sys.exit(1)
        
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Get database config from config.json
    db_config = config.get('database', {})
    
    # Create the data folder monitor
    data_monitor = DataFolderMonitor(
        data_folder=args.data_folder or db_config.get('data_folder', 'data'),
        db_name=args.db_name or db_config.get('default_db_name', 'loan_db.db'),
        table_name=args.table_name or db_config.get('default_table_name', 'loan_dt'),
        auto_create_folder=True
    )
    
    print(f"Starting monitor for folder: {data_monitor.data_folder}")
    print(f"Database: {data_monitor.db_name}, Default table: {data_monitor.table_name}")
    print(f"Interval: {args.interval} seconds")
    print("Press Ctrl+C to stop monitoring")
    
    # Process existing files first
    data_monitor.process_all_files()
    
    # Continuously watch for new files
    data_monitor.watch_folder(interval=args.interval)

if __name__ == "__main__":
    main() 