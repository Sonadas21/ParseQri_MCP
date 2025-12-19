# Import all agent classes for easier access
from agents.data_ingestion import DataIngestionAgent
from agents.schema_understanding import SchemaUnderstandingAgent
from agents.intent_classification import IntentClassificationAgent
from agents.sql_generation import SQLGenerationAgent 
from agents.sql_validation import SQLValidationAgent
from agents.query_execution import QueryExecutionAgent
from agents.response_formatting import ResponseFormattingAgent
from agents.visualization import VisualizationAgent

# These imports may fail if not all agents are implemented yet
try:
    from agents.data_preprocessing import DataPreprocessingAgent
except ImportError:
    pass

try:
    from agents.query_cache import QueryCacheAgent
except ImportError:
    pass

try:
    from agents.redis_cache import RedisCacheAgent
except ImportError:
    pass


try:
    from agents.schema_management import SchemaManagementAgent
except ImportError:
    pass

try:
    from agents.advanced_visualization import AdvancedVisualizationAgent
except ImportError:
    pass 