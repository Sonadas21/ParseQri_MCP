import ollama
import re
from models.data_models import QueryContext, AgentResponse

class IntentClassificationAgent:
    """
    Agent responsible for classifying user queries to determine if they require visualization or SQL.
    Uses an LLM to analyze query intent.
    """
    
    # def __init__(self, llm_model="llama3.1", api_base="http://localhost:11434"):
    def __init__(self, llm_model="PetrosStav/gemma3-tools:4b", api_base="http://localhost:11434"):
        """Initialize the Intent Classification Agent with the specified LLM model."""
        self.llm_model = llm_model
        ollama.api_base = api_base
        
    def process(self, context: QueryContext) -> AgentResponse:
        """Process the query context to classify user intent."""
        try:
            # Use pattern-based classification first for speed and reliability
            pattern_based_result = self._classify_query_by_pattern(context.user_question)
            if pattern_based_result is not None:
                needs_visualization = pattern_based_result
                classification_method = "pattern"
            else:
                # Fall back to LLM classification if pattern matching is inconclusive
                needs_visualization = self._classify_query_by_llm(context.user_question)
                classification_method = "llm"
            
            print(f"Query classified using {classification_method}-based method: Visualization needed = {needs_visualization}")
            
            # Return the classification result
            return AgentResponse(
                success=True,
                message="Query intent classified successfully",
                data={"needs_visualization": needs_visualization}
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Error in query classification: {str(e)}"
            )
    
    def _classify_query_by_pattern(self, user_question: str) -> bool:
        """
        Classify the user query using pattern matching to determine if visualization is required.
        
        Args:
            user_question: The user's natural language question
            
        Returns:
            True if visualization is needed, False if not needed, None if inconclusive
        """
        question = user_question.lower()
        
        # Explicit visualization request patterns
        visualization_terms = [
            'chart', 'graph', 'plot', 'visualization', 'visualisation', 'visually', 
            'pie', 'bar', 'histogram', 'scatter', 'line chart', 'heatmap', 'map', 
            'dashboard', 'infographic', 'diagram', 'display', 'show me', 'visual'
        ]
        
        # Check for explicit visualization requests
        for term in visualization_terms:
            if term in question:
                return True
        
        # Check for specific visualization phrases
        viz_phrases = [
            'display the results',
            'create a visualization',
            'display results',
            'show the data',
            'represent graphically',
            'graphical representation',
            'visualize the data',
            'visual representation',
            'display data'
        ]
        
        for phrase in viz_phrases:
            if phrase in question:
                return True
        
        # Check for explicit SQL-only request patterns
        sql_only_patterns = [
            'run query',
            'execute query',
            'sql query',
            'database query',
            'find the records',
            'retrieve the records',
            'list all',
            'count the number of',
            'select from',
            'fetch the',
            'get the records'
        ]
        
        for pattern in sql_only_patterns:
            if pattern in question:
                return False
        
        # If no conclusive pattern is found, return None to indicate inconclusive result
        return None
    
    def _classify_query_by_llm(self, user_question: str) -> bool:
        """
        Classify the user query using an LLM to determine if visualization is required.
        
        Args:
            user_question: The user's natural language question
            
        Returns:
            True if visualization is needed, False otherwise
        """
        prompt = """You are a query classification assistant with expertise in determining whether a user's query requires a visualization (e.g., charts, graphs, or visual explanations) or not.

Your task is to analyze the user's query and classify it into one of two categories:
1. **Visualization Required**: Respond with 'yes' if the query explicitly or implicitly requests a visualization.
2. **No Visualization Required**: Respond with 'no' if the query only requires information retrieval, explanation, or analysis without needing a visualization.

Examples of queries that require visualization:
- "Show me sales by region"
- "Compare the performance of different departments"
- "How many males vs females are in each department?"
- "What's the distribution of ages?"
- Any query asking for comparisons, distributions, trends, or patterns that would be better understood visually

Ensure your response is **only 'yes' or 'no'** (the answer should come first), followed by a brief explanation if necessary.

Query: """

        try:
            response = ollama.chat(model=self.llm_model, messages=[{
                "role": "user",
                "content": prompt + user_question
            }])
            
            if response and 'message' in response and 'content' in response['message']:
                content = response['message']['content'].lower().strip()
                
                # Check if the response starts with 'yes'
                if content.startswith('yes'):
                    return True
                else:
                    return False
            else:
                raise ValueError("Invalid response from LLM")
                
        except Exception as e:
            print(f"Error classifying query with LLM: {str(e)}")
            # Default to SQL query if classification fails
            return False
            
    def classify_query(self, user_question: str) -> bool:
        """
        Classify the user query to determine if visualization is required.
        Legacy method that combines pattern-based and LLM-based classification.
        
        Args:
            user_question: The user's natural language question
            
        Returns:
            True if visualization is needed, False otherwise
        """
        # First try pattern-based classification
        pattern_result = self._classify_query_by_pattern(user_question)
        if pattern_result is not None:
            return pattern_result
            
        # Fall back to LLM-based classification
        return self._classify_query_by_llm(user_question) 