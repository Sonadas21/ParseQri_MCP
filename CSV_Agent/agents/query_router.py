from typing import Dict, Any, Optional
from models.data_models import QueryContext, AgentResponse

class QueryRouterAgent:
    """
    Agent responsible for routing query processing through the metadata indexer
    and SQL generation pipeline with user context awareness.
    """
    
    def __init__(self):
        """Initialize the Query Router Agent."""
        pass
    
    def process(self, context: QueryContext) -> AgentResponse:
        """
        Process a query routing request by finding relevant metadata 
        and preparing context for SQL generation.
        
        Args:
            context: Query context object
            
        Returns:
            AgentResponse with routing results
        """
        try:
            if not context.user_id:
                return AgentResponse(
                    success=False,
                    message="User ID is required for query routing",
                    data={}
                )
            
            # Store original query in case we need to modify it
            original_query = context.user_question
            
            # We don't have direct access to agents here, routing instructions will
            # be included in the response for the orchestrator to handle
            
            # Return necessary instructions for continuing the pipeline
            return AgentResponse(
                success=True,
                message="Query routed successfully",
                data={
                    "next_steps": [
                        "metadata_indexer",  # First search for relevant metadata
                        "postgres_handler",  # Then ensure proper user context in SQL
                        "sql_generation"     # Finally generate SQL
                    ],
                    "original_query": original_query
                }
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Error in query routing: {str(e)}"
            )
    
    def enhance_query_with_metadata(self, context: QueryContext, metadata: Dict[str, Any]) -> str:
        """
        Enhance the original query with table and column metadata 
        to improve SQL generation without changing the user's intent.
        
        Args:
            context: Query context object
            metadata: Metadata from ChromaDB
            
        Returns:
            Enhanced query with metadata context
        """
        if not metadata:
            return context.user_question
        
        # Extract information from metadata
        table_name = metadata.get("table_name", "")
        columns = metadata.get("columns", [])
        
        # Create a string with column information
        columns_str = ", ".join(columns)
        
        # Create enhanced query with metadata context
        enhanced_query = (
            f"Given the table '{table_name}' with columns [{columns_str}], "
            f"answer the following question: {context.user_question}"
        )
        
        return enhanced_query 