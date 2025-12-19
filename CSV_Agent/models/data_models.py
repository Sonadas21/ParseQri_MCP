from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import pandas as pd

@dataclass
class QueryContext:
    """Main data structure passed between agents"""
    user_question: str
    db_name: str
    table_name: str
    user_id: str = None
    db_id: int = None  # Database ID for API integration
    schema: Dict[str, str] = None
    sql_query: str = None
    sql_valid: bool = False
    sql_issues: str = None
    query_results: Optional[pd.DataFrame] = None
    formatted_response: str = None
    visualization_data: Dict[str, Any] = None
    needs_visualization: bool = False
    cache_hit: bool = False

@dataclass
class AgentResponse:
    """Standard response format for all agents"""
    success: bool
    message: str
    data: Any = None 