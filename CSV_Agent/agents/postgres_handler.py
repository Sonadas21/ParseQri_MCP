import os
import pandas as pd
import sqlalchemy
from sqlalchemy import Column, MetaData, Table, create_engine, text, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.sql import select
from typing import Dict, List, Any, Optional, Tuple
from models.data_models import QueryContext, AgentResponse

class PostgresHandlerAgent:
    """
    Agent responsible for creating PostgreSQL tables with user_id columns
    and loading CSV data into the tables with the appropriate user_id.
    """
    
    def __init__(self, 
                db_url: str = "postgresql://postgres:postgres@localhost:5432/parseqri_db", 
                schema: str = "public"):
        """
        Initialize the PostgreSQL Handler Agent.
        
        Args:
            db_url: PostgreSQL connection URL
            schema: Database schema to use
        """
        self.db_url = db_url
        self.schema = schema
        self._create_engine()
    
    def _create_engine(self):
        """Create SQLAlchemy engine with specified connection parameters."""
        try:
            self.engine = create_engine(self.db_url)
            self.metadata = MetaData(schema=self.schema)
            print(f"PostgreSQL connection established successfully")
        except Exception as e:
            self.engine = None
            print(f"Error connecting to PostgreSQL: {e}")
    
    def process(self, context: QueryContext) -> AgentResponse:
        """Process the context for PostgreSQL operations"""
        try:
            if not context.user_id:
                return AgentResponse(
                    success=False,
                    message="User ID is required for PostgreSQL operations",
                    data={}
                )
            
            # Check for CSV file to process
            if hasattr(context, 'csv_file') and context.csv_file:
                # Process CSV file and create/populate table
                success, message, table_name = self.create_and_populate_table(
                    context.user_id, 
                    context.csv_file,
                    context.table_name
                )
                
                if not success:
                    return AgentResponse(
                        success=False,
                        message=f"Failed to process CSV file: {message}"
                    )
                
                # Update context with the actual table name used
                context.table_name = table_name
                
                return AgentResponse(
                    success=True,
                    message=f"Data loaded successfully into PostgreSQL table {table_name}",
                    data={"table_name": table_name}
                )
            
            # For SQL query execution (check if query has user_id condition)
            if hasattr(context, 'sql_query') and context.sql_query:
                # Ensure SQL query includes user_id filter
                updated_query = self.ensure_user_filter_in_query(
                    context.sql_query, context.user_id, context.table_name
                )
                
                # Update the context with the modified query
                context.sql_query = updated_query
                
                return AgentResponse(
                    success=True,
                    message="SQL query updated with user_id filter",
                    data={"sql_query": updated_query}
                )
            
            return AgentResponse(
                success=True,
                message="No specific PostgreSQL operation required",
                data={}
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Error in PostgreSQL handler: {str(e)}"
            )
    
    def create_and_populate_table(self, user_id: str, csv_path: str, 
                                 suggested_table_name: Optional[str] = None) -> Tuple[bool, str, str]:
        """
        Create a PostgreSQL table with user_id column and populate it with CSV data.
        
        Args:
            user_id: User identifier
            csv_path: Path to the CSV file
            suggested_table_name: Suggested name for the table (optional)
            
        Returns:
            Tuple of (success, message, actual_table_name)
        """
        try:
            # Read CSV file
            df = pd.read_csv(csv_path, low_memory=False)
            
            # Clean column names
            df.columns = [self._clean_column_name(col) for col in df.columns]
            
            # Determine table name
            table_name = suggested_table_name
            if not table_name:
                # Use file name without extension as table name
                base_name = os.path.basename(csv_path)
                table_name = os.path.splitext(base_name)[0]
            
            # Clean table name - ensure it's valid for PostgreSQL
            table_name = self._clean_table_name(table_name)
            
            # Add user_id prefix to ensure uniqueness
            qualified_table_name = f"{table_name}_{user_id}"
            # Truncate if needed (PostgreSQL has a 63 character limit on identifiers)
            qualified_table_name = qualified_table_name[:63]
            
            # Create user_id column and add it to the DataFrame
            df.insert(0, 'user_id', user_id)
            
            # Create table in PostgreSQL
            with self.engine.connect() as conn:
                # Check if table exists
                inspector = inspect(self.engine)
                if qualified_table_name in inspector.get_table_names(schema=self.schema):
                    # Drop existing table
                    conn.execute(text(f'DROP TABLE IF EXISTS "{self.schema}"."{qualified_table_name}"'))
                    conn.commit()
                
                # Create the table and insert data
                df.to_sql(
                    qualified_table_name,
                    conn,
                    schema=self.schema,
                    if_exists='replace',
                    index=False,
                    method='multi',
                    chunksize=1000
                )
                
                # Add a primary key or index on user_id for better performance
                try:
                    conn.execute(text(
                        f'CREATE INDEX idx_{qualified_table_name}_user_id ON "{self.schema}"."{qualified_table_name}" (user_id)'
                    ))
                    conn.commit()
                except Exception as idx_error:
                    print(f"Warning: Could not create index on user_id: {idx_error}")
            
            return True, "Table created and populated successfully", qualified_table_name
            
        except Exception as e:
            print(f"Error creating/populating table: {e}")
            return False, str(e), ""
    
    def ensure_user_filter_in_query(self, query: str, user_id: str, table_name: str) -> str:
        """
        Previously ensured the SQL query includes a filter for user_id.
        Now we don't add this filter since tables are already prefixed with user_id.
        
        Args:
            query: The SQL query to modify
            user_id: User identifier
            table_name: Table name
            
        Returns:
            SQL query without modifications
        """
        # Don't add user_id filter - tables are already user-specific with names like tablename_userid
        return query
        
        # Original implementation below, commented out
        """
        # Check if user_id is already in the query
        if f"user_id = '{user_id}'" in query or f'user_id = "{user_id}"' in query:
            return query
        
        # Simple SQL parser to modify WHERE clause
        query_lower = query.lower()
        
        # Check if query has a WHERE clause
        if " where " in query_lower:
            # Add AND user_id condition
            return query.replace(
                "WHERE", f"WHERE user_id = '{user_id}' AND", 1, 
            ).replace(
                "where", f"WHERE user_id = '{user_id}' AND", 1
            )
        
        # No WHERE clause, add one before GROUP BY, ORDER BY, LIMIT, etc.
        for clause in [" group by ", " order by ", " limit "]:
            if clause in query_lower:
                clause_pos = query_lower.find(clause)
                return f"{query[:clause_pos]} WHERE user_id = '{user_id}'{query[clause_pos:]}"
        
        # No clauses at all, add WHERE at the end
        return f"{query} WHERE user_id = '{user_id}'"
        """
    
    def _clean_column_name(self, col_name: str) -> str:
        """Clean column names for PostgreSQL compatibility"""
        col_name = col_name.lower()
        col_name = col_name.replace(' ', '_')
        col_name = col_name.replace('\n', '_')
        col_name = col_name.replace('/', '_')
        col_name = col_name.replace(',', '')
        col_name = col_name.replace('(', '')
        col_name = col_name.replace(')', '')
        # Ensure column name is not a reserved keyword
        if col_name in ["user", "order", "table", "column", "select", "from", "where"]:
            col_name = f"{col_name}_value"
        # Remove other special characters
        import re
        col_name = re.sub(r'[^\w]', '_', col_name)
        # Remove consecutive underscores
        col_name = re.sub(r'_+', '_', col_name)
        # Trim underscores from start and end
        col_name = col_name.strip('_')
        # Ensure name starts with a letter
        if col_name and not col_name[0].isalpha():
            col_name = f"col_{col_name}"
        # If empty, use a default name
        if not col_name:
            col_name = "column"
        return col_name
    
    def _clean_table_name(self, table_name: str) -> str:
        """Clean table name for PostgreSQL compatibility"""
        # Remove any characters that aren't alphanumeric or underscore
        import re
        table_name = re.sub(r'[^\w]', '_', table_name)
        # Ensure it starts with a letter
        if not table_name[0].isalpha():
            table_name = f"t_{table_name}"
        # Convert to lowercase
        return table_name.lower()
    
    def list_user_tables(self, user_id: str) -> List[str]:
        """
        List all tables for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of table names belonging to the user
        """
        try:
            tables = []
            with self.engine.connect() as conn:
                # Get all tables
                inspector = inspect(self.engine)
                all_tables = inspector.get_table_names(schema=self.schema)
                
                # Filter tables by user_id prefix
                for table in all_tables:
                    if table.startswith(f"{user_id}_"):
                        tables.append(table)
                        
                        # Get column information for verbose output
                        try:
                            columns = inspector.get_columns(table, schema=self.schema)
                            column_names = [col['name'] for col in columns]
                            print(f"  Table {table}: {len(column_names)} columns - {', '.join(column_names[:5])}" + 
                                 ("..." if len(column_names) > 5 else ""))
                        except Exception as col_err:
                            print(f"  Error fetching columns for {table}: {col_err}")
            
            return tables
            
        except Exception as e:
            print(f"Error listing user tables: {e}")
            return []
    
    def execute_query(self, query: str) -> Tuple[bool, Any]:
        """
        Execute an SQL query and return the results.
        
        Args:
            query: SQL query to execute
            
        Returns:
            Tuple of (success, result)
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                data = result.fetchall()
                columns = result.keys()
                
                # Convert to DataFrame
                df = pd.DataFrame(data, columns=columns)
                return True, df
                
        except Exception as e:
            print(f"Error executing query: {e}")
            return False, str(e) 