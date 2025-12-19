import ollama
import pandas as pd
from typing import Optional
from models.data_models import QueryContext, AgentResponse

class ResponseFormattingAgent:
    """
    Agent responsible for formatting query results into natural language responses.
    Uses an LLM to create human-readable explanations of SQL query results.
    """
    
    def __init__(self, llm_model="qwen3:4b", api_base="http://localhost:11434"):
        """Initialize the Response Formatting Agent with the specified LLM model."""
        self.llm_model = llm_model
        ollama.api_base = api_base
        
    def process(self, context: QueryContext) -> AgentResponse:
        """Process the query context to format the query results."""
        try:
            # Check if we have the required information
            if context.query_results is None:
                return AgentResponse(
                    success=False,
                    message="No query results provided for formatting"
                )
                
            # Format the query results
            formatted_response = self.format(context.query_results, context.user_question)
            
            if not formatted_response:
                return AgentResponse(
                    success=False,
                    message="Failed to format query results"
                )
                
            # Return the formatted response
            return AgentResponse(
                success=True,
                message="Query results formatted successfully",
                data={"formatted_response": formatted_response}
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Error in response formatting: {str(e)}"
            )
            
    def format(self, results: pd.DataFrame, user_query: str) -> Optional[str]:
        """
        Format the SQL query results into a natural language response.
        
        Args:
            results: DataFrame containing query results
            user_query: The user's original natural language question
            
        Returns:
            Formatted natural language response or None if formatting fails
        """
        # Convert results to a more readable format for the prompt
        results_str = results.to_json(orient='records', indent=2)
        
        prompt = (
            "You are an expert data analyst. Format the following query results into a natural language response.\n\n"
            f"User Question: {user_query}\n\n"
            f"Query Results:\n{results_str}\n\n"
            "Instructions:\n"
            "- Provide a clear, concise natural language response\n"
            "- Include specific numbers and values from the results\n"
            "- Format numbers appropriately (e.g., currency with 2 decimal places)\n"
            "- Make the response easy to understand for non-technical users\n"
            "- Do not include SQL syntax or technical jargon\n"
            "- Start with a direct answer to the question\n\n"
            "Format your response in a clear, professional manner."
        )

        try:
            response = ollama.chat(model=self.llm_model, messages=[{
                "role": "user",
                "content": prompt
            }])
            
            if response and 'message' in response and 'content' in response['message']:
                formatted_response = response['message']['content'].strip()
                return formatted_response
            else:
                raise ValueError("Invalid response from LLM")
                
        except Exception as e:
            print(f"Error formatting response: {str(e)}")
            return None 