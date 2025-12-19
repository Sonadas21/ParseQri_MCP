import pandas as pd
import sqlite3
from typing import Optional
from models.data_models import QueryContext, AgentResponse

class DataIngestionAgent:
    """
    Agent responsible for loading and processing data from various sources.
    Handles CSV loading, column name cleaning, and database conversion.
    """
    
    def __init__(self):
        """Initialize the Data Ingestion Agent."""
        pass
        
    def process(self, context: QueryContext) -> AgentResponse:
        """Process a data ingestion request."""
        try:
            # If we don't have a CSV file to process, assume it's already been done
            if not hasattr(context, 'csv_file') or not context.csv_file:
                return AgentResponse(
                    success=True,
                    message="No CSV file specified, skipping data ingestion",
                    data={}
                )
            
            # Check if user_id is provided for multi-user support
            if not hasattr(context, 'user_id') or not context.user_id:
                return AgentResponse(
                    success=False,
                    message="User ID is required for data ingestion in multi-user mode",
                    data={}
                )
                
            # Load CSV to DataFrame for validation
            df = self.load_csv_to_dataframe(context.csv_file)
            
            if df is None:
                return AgentResponse(
                    success=False,
                    message=f"Failed to load CSV file: {context.csv_file}"
                )
                
            # In the new flow, actual database operations are handled by PostgresHandlerAgent
            # This agent only validates and prepares the data
            row_count = len(df)
            
            return AgentResponse(
                success=True,
                message=f"CSV data validated with {row_count} rows, ready for database loading",
                data={"row_count": row_count, "csv_validated": True}
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Error in data ingestion: {str(e)}"
            )
            
    def load_csv_to_dataframe(self, csv_file: str) -> Optional[pd.DataFrame]:
        """
        Load a CSV file into a pandas DataFrame.
        
        Args:
            csv_file: Path to the CSV file
            
        Returns:
            DataFrame containing the CSV data or None if loading fails
        """
        try:
            df = pd.read_csv(csv_file, low_memory=False)
            print(f"CSV file {csv_file} loaded successfully.")
            return df
        except Exception as e:
            print(f"Error loading CSV file: {e}")
            return None
            
    def clean_column_name(self, col_name: str) -> str:
        """
        Clean column names by converting to lowercase and replacing special characters.
        
        Args:
            col_name: The column name to clean
            
        Returns:
            Cleaned column name
        """
        col_name = col_name.lower()
        col_name = col_name.replace(' ', '_')
        col_name = col_name.replace('\n', '_')
        col_name = col_name.replace('/', '_')
        col_name = col_name.replace(',', '')
        col_name = col_name.replace('(', '')
        col_name = col_name.replace(')', '')
        return col_name
        
    def convert_df_to_sqlite(self, df: pd.DataFrame, db_name: str, table_name: str) -> bool:
        """
        Convert a DataFrame to a SQLite database table.
        
        Args:
            df: The DataFrame to convert
            db_name: The name of the SQLite database
            table_name: The name of the table to create
            
        Returns:
            True if conversion was successful, False otherwise
        """
        try:
            # Clean the column names before saving to SQLite
            df.columns = [self.clean_column_name(col) for col in df.columns]
            
            with sqlite3.connect(db_name) as conn:
                df.to_sql(table_name, conn, if_exists='replace', index=False)
                print(f"Data successfully saved to {db_name}, table {table_name}.")
            return True
        except Exception as e:
            print(f"Error during conversion: {e}")
            return False 