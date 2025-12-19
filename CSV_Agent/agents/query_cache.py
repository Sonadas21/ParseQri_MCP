import os
import joblib
from pathlib import Path
from typing import Dict, Optional
from models.data_models import QueryContext, AgentResponse

class QueryCacheAgent:
    """
    Agent responsible for caching and retrieving previous queries.
    Helps improve performance by reusing results for repeated queries.
    """
    
    def __init__(self, cache_dir: str = "cache"):
        """
        Initialize the Query Cache Agent.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.query_cache = {}
        self._load_cache()
        
    def process(self, context: QueryContext) -> AgentResponse:
        """Process the query context to check for cached queries."""
        try:
            # Look for a cached query
            cached_query = self.get_cached_query(context.user_question)
            
            if cached_query:
                return AgentResponse(
                    success=True,
                    message="Query found in cache",
                    data={
                        "cache_hit": True,
                        "sql_query": cached_query
                    }
                )
            else:
                return AgentResponse(
                    success=True,
                    message="Query not found in cache",
                    data={
                        "cache_hit": False
                    }
                )
                
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Error in query cache: {str(e)}"
            )
            
    def cache_query(self, context: QueryContext):
        """
        Cache a successful query.
        
        Args:
            context: The query context containing the user question and SQL query
        """
        if not context.sql_query:
            return
            
        self.query_cache[context.user_question] = context.sql_query
        self._save_cache()
        
    def get_cached_query(self, query_text: str) -> Optional[str]:
        """
        Retrieve a cached SQL query for a given natural language query.
        
        Args:
            query_text: The natural language query
            
        Returns:
            The cached SQL query or None if not found
        """
        return self.query_cache.get(query_text)
        
    def _save_cache(self):
        """Save the cache to disk."""
        cache_path = self.cache_dir / "query_cache.joblib"
        joblib.dump(self.query_cache, cache_path)
        
    def _load_cache(self):
        """Load the cache from disk."""
        cache_path = self.cache_dir / "query_cache.joblib"
        if cache_path.exists():
            try:
                self.query_cache = joblib.load(cache_path)
            except Exception as e:
                print(f"Warning: Failed to load query cache: {str(e)}")
                self.query_cache = {} 