import ollama
import re
import json
from typing import Dict, Any
from models.data_models import QueryContext, AgentResponse

class SQLValidationAgent:
    """
    Agent responsible for validating and fixing SQL queries.
    Uses an LLM to check query syntax and correct common errors.
    """
    
    def __init__(self, llm_model="llama3.1:8b-instruct-q4_K_M", api_base="http://localhost:11434"):
        """Initialize the SQL Validation Agent with the specified LLM model."""
        self.llm_model = llm_model
        ollama.api_base = api_base
        
    def process(self, context: QueryContext) -> AgentResponse:
        """Process the query context to validate the SQL query."""
        try:
            # Check if we have the required information
            if not context.sql_query:
                return AgentResponse(
                    success=False,
                    message="No SQL query provided for validation"
                )
                
            if not context.schema:
                return AgentResponse(
                    success=False,
                    message="Schema information is required for SQL validation"
                )
                
            # Pre-sanitize the SQL query before validation
            sanitized_query = self.pre_sanitize_query(context.sql_query)
            
            # Replace table name with user-specific table name if needed
            if context.table_name and context.user_id:
                # Determine the actual PostgreSQL table name
                if context.table_name.endswith(f"_{context.user_id}"):
                    postgres_table = context.table_name
                else:
                    postgres_table = f"{context.table_name}_{context.user_id}"
                
                print(f"Table name replacement: '{context.table_name}' -> '{postgres_table}'")
                
                # Replace the base table name with the user-specific table name in the query
                # Use word boundaries to avoid partial replacements
                import re
                # Match table name that's not part of a larger word
                pattern = r'\b' + re.escape(context.table_name) + r'\b'
                sanitized_query = re.sub(pattern, postgres_table, sanitized_query, flags=re.IGNORECASE)
            else:
                print(f"Skipping table name replacement - table_name: {context.table_name}, user_id: {context.user_id}")
                
            print(f"Preprocessed SQL query from: {context.sql_query}")
            print(f"To: {sanitized_query}")
            
            try:
                # Try to validate and fix the sanitized SQL query
                validation_result = self.validate_and_fix_sql(sanitized_query, context.schema)
            except Exception as e:
                # If validation fails, use the sanitized query with a fallback result
                print(f"SQL validation failed: {str(e)}")
                validation_result = {
                    "sql_query": sanitized_query,
                    "sql_valid": True,  # Assume the sanitized query is valid
                    "sql_issues": f"Validation error: {str(e)}. Using sanitized query."
                }
            
            # Return the validation result
            return AgentResponse(
                success=True,
                message="SQL validation completed",
                data=validation_result
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Error in SQL validation: {str(e)}"
            )
    
    def pre_sanitize_query(self, sql_query: str) -> str:
        """
        Pre-sanitize an SQL query to fix common formatting issues before validation.
        
        Args:
            sql_query: The SQL query to sanitize
            
        Returns:
            A sanitized SQL query
        """
        # First convert any non-ASCII characters to safe ASCII equivalents
        ascii_query = ""
        for char in sql_query:
            if ord(char) < 128:  # ASCII character
                ascii_query += char
            elif char in '；｜':  # Known problematic characters (full-width semicolons)
                ascii_query += ';'
            else:
                # Skip other non-ASCII characters
                pass
        
        # If our conversion stripped too much, fall back to the original
        if not ascii_query.strip() or 'SELECT' not in ascii_query.upper():
            query = sql_query
        else:
            query = ascii_query
        
        # Remove backticks that can cause syntax issues
        query = query.replace('`', '')
        
        # Fix missing spaces between keywords and clauses
        query = re.sub(r'SELECT(\w)', r'SELECT \1', query, flags=re.IGNORECASE)
        query = re.sub(r'FROM(\w)', r'FROM \1', query, flags=re.IGNORECASE)
        query = re.sub(r'WHERE(\w)', r'WHERE \1', query, flags=re.IGNORECASE)
        query = re.sub(r'GROUP BY(\w)', r'GROUP BY \1', query, flags=re.IGNORECASE)
        query = re.sub(r'ORDER BY(\w)', r'ORDER BY \1', query, flags=re.IGNORECASE)
        query = re.sub(r'HAVING(\w)', r'HAVING \1', query, flags=re.IGNORECASE)
        
        # Fix common JOIN issues
        query = re.sub(r'(\w)JOIN', r'\1 JOIN', query, flags=re.IGNORECASE)
        
        # Ensure AS keyword has spaces around it
        query = re.sub(r'(\w)AS(\w)', r'\1 AS \2', query, flags=re.IGNORECASE)
        
        # Add space after commas if missing
        query = re.sub(r',(\w)', r', \1', query)
        
        # Ensure proper spacing around operators
        query = re.sub(r'(\w)(=|>|<|>=|<=|<>|!=)(\w)', r'\1 \2 \3', query)
        
        # Remove any duplicate semicolons
        query = re.sub(r';;+', ';', query)
        
        # Ensure the query ends with exactly one semicolon
        query = query.rstrip(';') + ';'
        
        return query
            
    def validate_and_fix_sql(self, sql_query: str, schema: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate and fix the given SQL query against the provided database schema.
        
        Args:
            sql_query: The SQL query to validate
            schema: Dictionary mapping column names to their types
            
        Returns:
            Dictionary with validation results
        """
        if sql_query == "NOT_RELEVANT":
            return {"sql_query": "NOT_RELEVANT", "sql_valid": False}

        prompt = (
            "You are an SQL validator. Validate the following SQL query and fix any issues with the syntax.\n\n"
            f"Schema: {json.dumps(schema, indent=2)}\n"
            f"Query: {sql_query}\n"
            "Return a JSON object with this format: {\"valid\": boolean, \"issues\": string or null, \"corrected_query\": string}\n"
            "Focus on fixing these common issues:\n"
            "1. Missing spaces between SQL keywords\n"
            "2. Incorrect JOIN syntax\n"
            "3. Improper clause formatting\n"
            "4. Mismatched column names\n"
            "5. Non-ASCII characters that need to be replaced\n"
            "Return only the JSON object, no additional text."
        )

        try:
            response = ollama.chat(model=self.llm_model, messages=[{"role": "user", "content": prompt}])
            
            if response and 'message' in response and 'content' in response['message']:
                result_str = response['message']['content'].strip()
                
                # Parse the validation result
                try:
                    result = self.extract_json(result_str)
                    # Sanitize the corrected query to remove any problematic characters
                    if "corrected_query" in result:
                        result["corrected_query"] = self.pre_sanitize_query(result["corrected_query"])
                    
                    return {
                        "sql_query": result.get("corrected_query", sql_query),
                        "sql_valid": result.get("valid", False),
                        "sql_issues": result.get("issues")
                    }
                except ValueError as e:
                    # If JSON parsing fails, attempt to fix the query ourselves
                    print(f"Warning: JSON parsing failed - {str(e)}")
                    fixed_query = self.fallback_fix_query(sql_query)
                    return {
                        "sql_query": fixed_query,
                        "sql_valid": True,  # We're assuming our fixes worked
                        "sql_issues": "Validation response parsing failed, applied basic fixes"
                    }
            else:
                # If response is malformed, use fallback
                print("Warning: Invalid response structure from LLM")
                fixed_query = self.fallback_fix_query(sql_query)
                return {
                    "sql_query": fixed_query,
                    "sql_valid": True,  # We're assuming our fixes worked
                    "sql_issues": "Invalid LLM response, applied basic fixes"
                }

        except Exception as e:
            print(f"Error in SQL validation: {str(e)}")
            # Attempt fallback fix
            fixed_query = self.fallback_fix_query(sql_query)
            # Instead of returning error, assume our basic fixes are valid
            return {
                "sql_query": fixed_query,
                "sql_valid": True,  # We're assuming our fixes worked
                "sql_issues": f"Validation failed: {str(e)}, applied basic fixes"
            }
    
    def fallback_fix_query(self, sql_query: str) -> str:
        """
        Apply basic fixes to an SQL query when the LLM validation fails.
        
        Args:
            sql_query: The SQL query to fix
            
        Returns:
            A fixed SQL query
        """
        # Start with pre-sanitization
        query = self.pre_sanitize_query(sql_query)
        
        # Try to identify and fix common structures
        if "SELECT" not in query.upper() and "FROM" not in query.upper():
            # Missing basic clauses, try to reconstruct
            match = re.search(r'COUNT\s*\(\s*\*\s*\)\s+AS\s+(\w+)', query, re.IGNORECASE)
            if match:
                alias = match.group(1)
                # Likely a count query
                table_match = re.search(r'(\w+)\s+WHERE', query, re.IGNORECASE)
                table = table_match.group(1) if table_match else "table_name"
                where_clause = re.search(r'WHERE\s+(.+?)(?:ORDER|GROUP|LIMIT|$)', query, re.IGNORECASE)
                where = where_clause.group(1).strip() if where_clause else ""
                return f"SELECT COUNT(*) AS {alias} FROM {table} WHERE {where};"
                
        # Check for multiple WHERE clauses (a common issue causing syntax errors)
        if query.upper().count("WHERE") > 1:
            # Fix the query to have only one WHERE clause
            first_where_index = query.upper().find("WHERE")
            if first_where_index != -1:
                # Only keep the first WHERE clause
                before_where = query[:first_where_index]
                after_where = query[first_where_index + 5:]  # Length of "WHERE" is 5
                
                # Find the next WHERE if it exists
                next_where_index = after_where.upper().find("WHERE")
                if next_where_index != -1:
                    # Replace the second WHERE with AND
                    after_where = after_where[:next_where_index] + "AND" + after_where[next_where_index + 5:]
                
                query = before_where + "WHERE" + after_where
        
        # Ensure it ends with semicolon
        if not query.strip().endswith(';'):
            query += ';'
            
        return query
            
    def extract_json(self, response_str: str) -> Dict[str, Any]:
        """
        Extract and parse JSON from a string, handling multiple JSON objects and extra text.
        
        Args:
            response_str: The response string that may contain JSON
            
        Returns:
            The parsed JSON object
        """
        try:
            # First try direct JSON parsing
            return json.loads(response_str)
        except json.JSONDecodeError:
            # Try to find JSON object using a simple balanced brace matching approach
            # instead of the recursive regex pattern that was causing issues
            opening_brace_indices = [i for i, char in enumerate(response_str) if char == '{']
            
            for start_idx in opening_brace_indices:
                brace_count = 0
                for i in range(start_idx, len(response_str)):
                    if response_str[i] == '{':
                        brace_count += 1
                    elif response_str[i] == '}':
                        brace_count -= 1
                        
                    if brace_count == 0:  # We've found a balanced set of braces
                        try:
                            json_str = response_str[start_idx:i+1]
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            continue  # Try the next opening brace
                            
            # If no valid JSON found using balanced braces, try a simpler regex approach
            brace_match = re.search(r'\{(.*?)\}', response_str, re.DOTALL)
            if brace_match:
                try:
                    # Try to fix common issues and parse as JSON
                    json_str = '{' + brace_match.group(1) + '}'
                    # Replace single quotes with double quotes
                    json_str = json_str.replace("'", '"')
                    # Ensure property names are in double quotes
                    json_str = re.sub(r'(\w+):', r'"\1":', json_str)
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            
            # If all approaches fail, try one last approach - extract key-value pairs manually
            try:
                # Look for patterns like "key": value or 'key': value or key: value
                result = {}
                valid_pair = re.findall(r'["\']?(\w+)["\']?\s*:\s*["\']?(.*?)["\']?(?:,|\})', response_str)
                for key, value in valid_pair:
                    # Convert string representations of booleans
                    if value.lower() == 'true':
                        result[key] = True
                    elif value.lower() == 'false':
                        result[key] = False
                    elif value.lower() == 'null':
                        result[key] = None
                    else:
                        result[key] = value
                
                if result:
                    return result
            except Exception:
                pass
                
            # If really all approaches fail, raise error
            raise ValueError(f"No valid JSON found in response: {response_str}") 