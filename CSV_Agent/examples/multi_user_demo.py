#!/usr/bin/env python
"""
Multi-User Metadata Indexing Demo for ParseQri
=============================================

This script demonstrates how to use the user-based metadata indexing
features in ParseQri to support multiple users with their own data
and queries.

Usage:
    python multi_user_demo.py

The script performs the following steps:
1. Upload sample data for two different users
2. Extract metadata using LLM and store in ChromaDB 
3. Create PostgreSQL tables with user_id columns
4. Query each user's data separately
"""

import os
import sys
import pandas as pd
import time
import subprocess
import argparse
from pathlib import Path

# Add parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from core.orchestrator import TextSQLOrchestrator
from models.data_models import QueryContext, AgentResponse


def create_sample_data(output_dir="sample_data"):
    """Create sample data files for different users"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Sample 1: User 1 - Sales Data
    sales_data = pd.DataFrame({
        'date': pd.date_range(start='2023-01-01', periods=10),
        'product': ['Laptop', 'Mouse', 'Keyboard', 'Monitor', 'Headphones', 
                    'Phone', 'Tablet', 'Charger', 'Case', 'Speaker'],
        'category': ['Electronics', 'Accessories', 'Accessories', 'Electronics', 'Accessories',
                     'Electronics', 'Electronics', 'Accessories', 'Accessories', 'Electronics'],
        'price': [1200, 25, 80, 350, 100, 800, 500, 30, 20, 120],
        'quantity': [2, 10, 5, 3, 8, 4, 3, 15, 12, 6]
    })
    sales_file = os.path.join(output_dir, "user1_sales.csv")
    sales_data.to_csv(sales_file, index=False)
    print(f"Created sample sales data for user1: {sales_file}")
    
    # Sample 2: User 2 - Employee Data
    employee_data = pd.DataFrame({
        'employee_id': range(1001, 1011),
        'name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Evan', 
                'Fiona', 'George', 'Hannah', 'Ian', 'Julia'],
        'department': ['Engineering', 'Sales', 'Marketing', 'HR', 'Finance',
                      'Engineering', 'Sales', 'Marketing', 'HR', 'Finance'],
        'salary': [85000, 75000, 70000, 65000, 90000, 
                  82000, 78000, 72000, 67000, 95000],
        'hire_date': pd.date_range(start='2020-01-15', periods=10, freq='30D')
    })
    employee_file = os.path.join(output_dir, "user2_employees.csv")
    employee_data.to_csv(employee_file, index=False)
    print(f"Created sample employee data for user2: {employee_file}")
    
    return sales_file, employee_file


def run_demo():
    """Run the multi-user metadata indexing demo"""
    print("\n" + "="*80)
    print("ParseQri Multi-User Metadata Indexing Demo")
    print("="*80)
    
    # Create sample data
    print("\nStep 1: Creating sample data for two different users")
    sales_file, employee_file = create_sample_data()
    
    # Initialize orchestrator
    orchestrator = TextSQLOrchestrator("../config.json")
    
    # Upload data for user1
    print("\nStep 2: Uploading sales data for user1")
    user1_id = "user1"
    user1_context = orchestrator.process_upload(
        csv_file=sales_file,
        user_id=user1_id,
        suggested_table_name="sales"
    )
    
    print(f"  Data loaded to table: {user1_context.table_name}")
    time.sleep(1)  # Brief pause for readability
    
    # Upload data for user2
    print("\nStep 3: Uploading employee data for user2")
    user2_id = "user2"
    user2_context = orchestrator.process_upload(
        csv_file=employee_file,
        user_id=user2_id,
        suggested_table_name="employees"
    )
    
    print(f"  Data loaded to table: {user2_context.table_name}")
    time.sleep(1)  # Brief pause for readability
    
    # List available tables for both users
    print("\nStep 4: Listing available tables for each user")
    
    # Get tables for user1
    if 'postgres_handler' in orchestrator.agents:
        postgres_handler = orchestrator.agents['postgres_handler']
        user1_tables = postgres_handler.list_user_tables(user1_id)
        user2_tables = postgres_handler.list_user_tables(user2_id)
        
        print(f"\nUser1 tables: {', '.join(user1_tables)}")
        print(f"User2 tables: {', '.join(user2_tables)}")
    
    # Execute a query for user1
    print("\nStep 5: Executing a query for user1 (sales data)")
    user1_query = "What's the total revenue for each product category?"
    
    print(f"  Query: {user1_query}")
    user1_result = orchestrator.process_query(
        user_question=user1_query,
        db_name="",  # Not used with PostgreSQL
        table_name="",  # Will be determined from metadata
        user_id=user1_id
    )
    
    print("  SQL Query:")
    print(f"  {user1_result.sql_query}")
    print("\n  Results:")
    print(f"  {user1_result.formatted_response}")
    time.sleep(2)  # Brief pause for readability
    
    # Execute a query for user2
    print("\nStep 6: Executing a query for user2 (employee data)")
    user2_query = "What's the average salary by department?"
    
    print(f"  Query: {user2_query}")
    user2_result = orchestrator.process_query(
        user_question=user2_query,
        db_name="",  # Not used with PostgreSQL
        table_name="",  # Will be determined from metadata
        user_id=user2_id
    )
    
    print("  SQL Query:")
    print(f"  {user2_result.sql_query}")
    print("\n  Results:")
    print(f"  {user2_result.formatted_response}")
    
    # Test cross-user query security
    print("\nStep 7: Testing cross-user query security")
    security_query = "Show me all data from employees table"
    
    print(f"  Attempting to access user2 data with user1 credentials")
    print(f"  Query: {security_query}")
    security_result = orchestrator.process_query(
        user_question=security_query,
        db_name="",
        table_name="employees",  # Explicitly trying to access user2's table
        user_id=user1_id  # But with user1's credentials
    )
    
    print("  Results:")
    if hasattr(security_result, 'query_results') and security_result.query_results is not None:
        if len(security_result.query_results) > 0:
            print("  ❌ SECURITY FAILURE: user1 was able to access user2's data!")
        else:
            print("  ✅ SECURITY SUCCESS: user1 could not access user2's data (empty results)")
    else:
        print("  ✅ SECURITY SUCCESS: user1 could not access user2's data (no results)")
        
    print("\nDemo completed successfully!")


if __name__ == "__main__":
    # Check if we're in the right directory or if we need to move to the parent
    current_dir = os.path.basename(os.getcwd())
    if current_dir == "examples":
        os.chdir("..")
        
    # Create examples directory if it doesn't exist
    os.makedirs("examples", exist_ok=True)
    
    # Run the demo
    run_demo() 