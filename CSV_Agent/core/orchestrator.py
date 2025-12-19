from typing import Dict, Any, Optional
from models.data_models import QueryContext, AgentResponse
import importlib

class TextSQLOrchestrator:
    """Main orchestrator that coordinates the agent workflow"""
    
    def __init__(self, config_path: str):
        """Initialize the orchestrator with configuration"""
        self.config = self._load_config(config_path)
        self.agents = {}
        self._load_agents()
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        import json
        with open(config_path, 'r') as f:
            return json.load(f)
        
    def _load_agents(self):
        """Dynamically load all required agents based on configuration"""
        for agent_id, agent_config in self.config['agents'].items():
            module_path = agent_config['module']
            class_name = agent_config['class']
            
            # Dynamically import the agent class
            module = importlib.import_module(module_path)
            agent_class = getattr(module, class_name)
            
            # Initialize agent with its config
            self.agents[agent_id] = agent_class(**agent_config.get('params', {}))
    
    def process_query(self, user_question: str, db_name: str, table_name: str, 
                     user_id: str = None, force_visualization: bool = False) -> QueryContext:
        """Process a natural language query through the agent pipeline"""
        # Initialize query context with user_id for multi-user support
        # (user ID validation will be handled by individual agents)
        context = QueryContext(
            user_question=user_question,
            db_name=db_name,
            table_name=table_name,
            user_id=user_id
        )
        
        if user_id:
            print(f"Processing query for user: {user_id}")
        else:
            print("Processing query without specified user ID (will be determined automatically)")
        
        # First check the cache
        if 'query_cache' in self.agents:
            cache_response = self.agents['query_cache'].process(context)
            if cache_response.success and cache_response.data.get('cache_hit'):
                cached_data = cache_response.data.get('cached_data', {})
                context.cache_hit = True
                
                # Debug: Show what's in the cache
                print(f"[Cache] Cached data keys: {cached_data.keys()}")
                print(f"[Cache] SQL query: {cached_data.get('sql_query', 'NONE')}")
                print(f"[Cache] Formatted response: {cached_data.get('formatted_response', 'NONE')[:100] if cached_data.get('formatted_response') else 'NONE'}")
                
                # Restore all cached data
                context.sql_query = cached_data.get('sql_query')
                context.formatted_response = cached_data.get('formatted_response')
                context.table_name = cached_data.get('table_name', context.table_name)
                context.db_name = cached_data.get('db_name', context.db_name)
                
                # Restore query results if available
                if 'query_results' in cached_data and cached_data['query_results']:
                    import pandas as pd
                    context.query_results = pd.DataFrame(cached_data['query_results'])
                    print(f"[Cache] Restored {len(context.query_results)} query result rows")
                
                print(f"✅ Cache hit! Returning cached response (saved execution + formatting)")
                return context


        
        # Route the query through metadata indexer if user_id is provided
        if user_id and 'query_router' in self.agents:
            router_response = self.agents['query_router'].process(context)
            if router_response.success:
                # Get recommended next steps
                next_steps = router_response.data.get('next_steps', [])
                
                # First, find relevant metadata for this query
                if 'metadata_indexer' in next_steps and 'metadata_indexer' in self.agents:
                    metadata_response = self.agents['metadata_indexer'].process(context)
                    if metadata_response.success and metadata_response.data.get('relevant_metadata'):
                        # Add relevant metadata to context
                        context.relevant_metadata = metadata_response.data['relevant_metadata']
                        print(f"Found relevant metadata for table: {context.relevant_metadata.get('table_name')}")
                        
                        # Update table name if needed
                        metadata_table = context.relevant_metadata.get('table_name')
                        if metadata_table and metadata_table != context.table_name:
                            print(f"Updating table name from {context.table_name} to {metadata_table}")
                            context.table_name = metadata_table
                
                # Then, ensure PostgreSQL user context
                if 'postgres_handler' in next_steps and 'postgres_handler' in self.agents:
                    postgres_response = self.agents['postgres_handler'].process(context)
                    if not postgres_response.success:
                        print(f"Warning: PostgreSQL handler issue: {postgres_response.message}")
        
        # Determine query intent
        if 'intent_classifier' in self.agents:
            intent_response = self.agents['intent_classifier'].process(context)
            if not intent_response.success:
                return self._handle_error(context, "Failed to classify query intent")
            
            # Allow forcing visualization by parameter
            if force_visualization:
                context.needs_visualization = True
                print("Forcing visualization mode based on query content or flags")
            else:
                context.needs_visualization = intent_response.data.get('needs_visualization', False)
        
        if context.needs_visualization:
            # Process visualization request
            return self._process_visualization(context)
        else:
            # Process SQL query
            return self._process_sql_query(context)
    
    def process_upload(self, csv_file: str, user_id: str = None, suggested_table_name: str = None, db_id: int = None) -> QueryContext:
        """
        Process a CSV upload through the agent pipeline with user context.
        
        Args:
            csv_file: Path to the CSV file to process
            user_id: User identifier for multi-user support
            suggested_table_name: Optional suggested name for the table
            db_id: Optional database ID for API integration
            
        Returns:
            QueryContext with processing results
        """
        # Initialize context for upload processing (user ID validation will be handled by individual agents)
        context = QueryContext(
            user_question="",  # No question for uploads
            db_name="",  # Will be determined by PostgreSQL handler
            table_name=suggested_table_name or "",  # May be determined by metadata
            user_id=user_id
        )
        
        if user_id:
            print(f"Processing CSV upload for user: {user_id}")
        else:
            print("Processing CSV upload without specified user ID (will be determined automatically)")
        
        # Add CSV file path to context
        context.csv_file = csv_file
        
        # Add database ID to context if provided
        if db_id is not None:
            context.db_id = db_id
            print(f"Processing with database ID: {db_id}")
        
        # Step 1: Data validation with the data ingestion agent
        if 'data_ingestion' in self.agents:
            ingestion_response = self.agents['data_ingestion'].process(context)
            if not ingestion_response.success:
                return self._handle_error(context, f"Data ingestion failed: {ingestion_response.message}")
        
        # Step 2: Extract metadata using the metadata indexer
        if 'metadata_indexer' in self.agents:
            metadata_response = self.agents['metadata_indexer'].process(context)
            if metadata_response.success and metadata_response.data.get('metadata'):
                metadata = metadata_response.data['metadata']
                
                # Update table name from metadata if available
                if suggested_table_name is None and 'table_name' in metadata:
                    context.table_name = metadata['table_name']
                    print(f"Using table name from metadata: {context.table_name}")
                
                # Add database ID to metadata if provided
                if db_id is not None and 'metadata' in metadata_response.data:
                    metadata_response.data['metadata']['db_id'] = db_id
            else:
                print(f"Warning: Metadata extraction issue: {metadata_response.message}")
        
        # Step 3: Create PostgreSQL table and load data
        if 'postgres_handler' in self.agents:
            postgres_response = self.agents['postgres_handler'].process(context)
            if not postgres_response.success:
                return self._handle_error(context, f"PostgreSQL operation failed: {postgres_response.message}")
            
            # Update table name from PostgreSQL response if available
            if postgres_response.data and 'table_name' in postgres_response.data:
                context.table_name = postgres_response.data['table_name']
        
        return context
    
    def _process_visualization(self, context: QueryContext) -> QueryContext:
        """Process a visualization request"""
        # Get schema information
        if 'schema_understanding' in self.agents:
            schema_response = self.agents['schema_understanding'].process(context)
            if not schema_response.success:
                return self._handle_error(context, "Failed to retrieve schema")
            
            context.schema = schema_response.data.get('schema')
        
        # Generate visualization
        if 'visualization' in self.agents:
            viz_response = self.agents['visualization'].process(context)
            if not viz_response.success:
                return self._handle_error(context, "Failed to generate visualization")
            
            context.visualization_data = viz_response.data
        
        return context
    
    def _process_sql_query(self, context: QueryContext) -> QueryContext:
        """Process an SQL query request"""
        # Get schema information
        if 'schema_understanding' in self.agents:
            schema_response = self.agents['schema_understanding'].process(context)
            if not schema_response.success:
                return self._handle_error(context, "Failed to retrieve schema")
            
            context.schema = schema_response.data.get('schema')
        
        # Generate SQL query
        if 'sql_generation' in self.agents:
            sql_response = self.agents['sql_generation'].process(context)
            if not sql_response.success:
                return self._handle_error(context, "Failed to generate SQL query")
            
            context.sql_query = sql_response.data.get('sql_query')
        
        # Validate SQL query
        if 'sql_validation' in self.agents:
            validation_response = self.agents['sql_validation'].process(context)
            context.sql_valid = validation_response.data.get('sql_valid', False)
            context.sql_issues = validation_response.data.get('sql_issues')
            
            # Update the query with the corrected/validated version
            if validation_response.success and validation_response.data.get('sql_query'):
                context.sql_query = validation_response.data.get('sql_query')
                print(f"Using validated SQL query: {context.sql_query}")
            
            if not context.sql_valid:
                return self._handle_error(context, f"SQL validation failed: {context.sql_issues}")
        
        # Apply user context with PostgreSQL handler
        if context.user_id and 'postgres_handler' in self.agents:
            postgres_response = self.agents['postgres_handler'].process(context)
            if postgres_response.success and postgres_response.data.get('sql_query'):
                context.sql_query = postgres_response.data.get('sql_query')
        
        # Execute the query
        if 'query_execution' in self.agents:
            execution_response = self.agents['query_execution'].process(context)
            if not execution_response.success:
                return self._handle_error(context, "Failed to execute SQL query")
            
            context.query_results = execution_response.data.get('query_results')
        
        # Format the response
        if 'response_formatting' in self.agents:
            formatting_response = self.agents['response_formatting'].process(context)
            if not formatting_response.success:
                return self._handle_error(context, "Failed to format response")
            
            context.formatted_response = formatting_response.data.get('formatted_response')
        
        # Cache the successful query
        if 'query_cache' in self.agents:
            print(f"[Orchestrator] About to cache - user_id={context.user_id}, table_name={context.table_name}")
            self.agents['query_cache'].cache_query(context)

        
        return context
    
    def _execute_cached_query(self, context: QueryContext) -> QueryContext:
        """Execute a cached query and format the response"""
        # Execute the query
        if 'query_execution' in self.agents:
            execution_response = self.agents['query_execution'].process(context)
            if not execution_response.success:
                return self._handle_error(context, "Failed to execute cached SQL query")
            
            context.query_results = execution_response.data.get('query_results')
        
        # Format the response
        if 'response_formatting' in self.agents:
            formatting_response = self.agents['response_formatting'].process(context)
            if not formatting_response.success:
                return self._handle_error(context, "Failed to format response for cached query")
            
            context.formatted_response = formatting_response.data.get('formatted_response')
        
        return context
    
    def _handle_error(self, context: QueryContext, error_message: str) -> QueryContext:
        """Handle errors during processing"""
        print(f"Error: {error_message}")
        
        # Check if it's a database connection error
        if "unable to open database file" in error_message.lower():
            error_message = "Unable to connect to database. Ensure the PostgreSQL service is running and properly configured."
            
            # Add remediation instructions
            print("\nRemediation steps:")
            print("1. Check that PostgreSQL is running")
            print("2. Verify database credentials in config.json")
            print("3. Confirm that the user has permissions to access the database")
            print("4. Ensure the table exists for the specified user")
        
        # Check if it's a table not found error
        elif "failed to retrieve schema" in error_message.lower() or "no table name found" in error_message.lower():
            # Add remediation instructions
            print("\nRemediation steps:")
            print(f"1. Upload data first for user '{context.user_id}' with:")
            print(f"   python main.py --upload path/to/file.csv --user {context.user_id} --table [table_name]")
            print("2. Check if the table exists with:")
            print(f"   python main.py --list-tables --user {context.user_id}")
            print("3. Make sure the table name you're querying is correct")
        
        context.formatted_response = f"Error: {error_message}"
        return context 