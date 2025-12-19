import os
import json
import pandas as pd
import chromadb
import ollama
from typing import Dict, List, Any, Tuple, Optional
from models.data_models import QueryContext, AgentResponse
from pathlib import Path

class MetadataIndexerAgent:
    """
    Agent responsible for extracting metadata from CSV files,
    storing it in ChromaDB with user-based indexing, and
    searching for relevant metadata during query processing.
    """
    
    def __init__(self, llm_model="PetrosStav/gemma3-tools:4b", api_base="http://localhost:11434", 
                 chroma_persist_dir="../data/db_storage"):
        """Initialize the Metadata Indexer Agent with model and storage config."""
        self.llm_model = llm_model
        ollama.api_base = api_base
        self.chroma_persist_dir = chroma_persist_dir
        
        # Ensure directory exists
        os.makedirs(chroma_persist_dir, exist_ok=True)
        
        # We'll create separate ChromaDB clients for each user as needed
        self.chroma_clients = {}
        self.collections = {}
        
    def _get_user_collection(self, user_id):
        """Get or create a user-specific ChromaDB collection"""
        if user_id in self.collections:
            return self.collections[user_id]
            
        # Create user directory if it doesn't exist
        user_dir = os.path.join(self.chroma_persist_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        
        # Create or get client for this user
        if user_id not in self.chroma_clients:
            try:
                print(f"Creating ChromaDB client at path: {user_dir}")
                self.chroma_clients[user_id] = chromadb.PersistentClient(path=user_dir)
                print(f"ChromaDB client created successfully")
            except Exception as e:
                print(f"Error creating ChromaDB client: {str(e)}, {type(e).__name__}")
                raise
        
        # Create or get collection for this user
        try:
            print(f"Attempting to get collection: {user_id}_metadata")
            collection = self.chroma_clients[user_id].get_collection(f"{user_id}_metadata")
            print(f"Successfully retrieved existing collection")
        except Exception as e:
            print(f"Collection not found, error: {str(e)}, {type(e).__name__}")
            try:
                print(f"Attempting to create new collection: {user_id}_metadata")
                collection = self.chroma_clients[user_id].create_collection(
                    name=f"{user_id}_metadata",
                    metadata={"hnsw:space": "cosine", "user_id": user_id}
                )
                print(f"Successfully created new collection")
            except Exception as e:
                print(f"Failed to create collection: {str(e)}, {type(e).__name__}")
                raise
            
        self.collections[user_id] = collection
        return collection
    
    def process(self, context: QueryContext) -> AgentResponse:
        """Process the context and handle metadata operations."""
        try:
            if not context.user_id:
                return AgentResponse(
                    success=False,
                    message="User ID is required for metadata operations",
                    data={}
                )
            
            # Get the collection for this user
            collection = self._get_user_collection(context.user_id)
            
            # Check if we have a CSV file to process (metadata extraction mode)
            if hasattr(context, 'csv_file') and context.csv_file:
                # Extract metadata from CSV
                metadata = self.extract_metadata_with_llm(context.csv_file)
                
                if not metadata:
                    return AgentResponse(
                        success=False,
                        message=f"Failed to extract metadata from CSV file: {context.csv_file}"
                    )
                
                # Save metadata to user's ChromaDB
                document_id = self.save_metadata_to_chroma(
                    context.user_id, 
                    metadata.get("table_name", context.table_name),
                    metadata.get("columns", {})
                )
                
                # Create log file in user's db directory
                user_db_dir = os.path.join(self.chroma_persist_dir, context.user_id)
                log_file = os.path.join(user_db_dir, f"metadata_{Path(context.csv_file).stem}.json")
                
                # Save the complete metadata to the log file
                with open(log_file, 'w') as f:
                    json.dump({
                        "user_id": context.user_id,
                        "table_name": metadata.get("table_name", context.table_name),
                        "csv_file": context.csv_file,
                        "document_id": document_id,
                        "metadata": metadata
                    }, f, indent=2)
                
                return AgentResponse(
                    success=True,
                    message="Metadata extracted and saved successfully",
                    data={"metadata": metadata, "document_id": document_id}
                )
            
            # Otherwise, search for relevant metadata (query mode)
            relevant_metadata = self.search_relevant_metadata(
                context.user_id, context.user_question
            )
            
            return AgentResponse(
                success=True,
                message="Relevant metadata retrieved successfully",
                data={"relevant_metadata": relevant_metadata}
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Error in metadata indexer: {str(e)}"
            )
    
    def extract_metadata_with_llm(self, csv_path: str) -> Dict[str, Any]:
        """
        Extract metadata from a CSV file using LLM inference.
        
        Args:
            csv_path: Path to the CSV file
            
        Returns:
            Dictionary containing table_name and columns with descriptions
        """
        try:
            # Read first few rows of CSV to analyze structure
            df = pd.read_csv(csv_path, nrows=10)
            
            print(f"Successfully loaded CSV with columns: {list(df.columns)}")
            
            # Try LLM approach, but if it fails, use fallback
            try:
                # Get column data types and sample values
                column_info = {}
                for column in df.columns:
                    data_type = str(df[column].dtype)
                    sample_values = df[column].dropna().head(3).tolist()
                    sample_values_str = ", ".join([str(val) for val in sample_values])
                    column_info[column] = {
                        "data_type": data_type,
                        "sample_values": sample_values_str
                    }
                
                # Generate sample data summary
                column_summary = "\n".join([
                    f"Column: {col}\nData Type: {info['data_type']}\nSample Values: {info['sample_values']}" 
                    for col, info in column_info.items()
                ])
                
                # Create improved prompt for LLM
                prompt = f"""
                Task: Analyze CSV data and generate clean, simple metadata

                CSV File Analysis:
                {column_summary}

                Instructions:
                1. Identify a clear, concise table name that describes this dataset (avoid using 'data', 'table', or generic names)
                2. For each column, provide a simple, clear description (max 10 words)
                   - Focus on WHAT the column contains, not technical details
                   - Use plain, non-technical language
                   - Avoid mentioning data types, formats, or technical jargon

                Response Format (JSON only):
                {{
                  "table_name": "name_user_id",
                  "columns": {{
                    "column1": "Simple description of what this contains",
                    "column2": "Simple description of what this contains",
                    ...
                  }}
                }}

                Important Rules:
                - Return ONLY valid JSON, no explanation or other text
                - Use snake_case for the table_name
                - Table name MUST NOT start with a number (PostgreSQL requirement)
                - Keep descriptions very simple and clear
                - Do NOT include data types in descriptions
                - Do NOT use technical jargon or database terminology
                - Descriptions should be readable by non-technical users
                """
                
                print(f"Sending prompt to LLM model: {self.llm_model}")
                
                # Call LLM for inference
                try:
                    response = ollama.chat(
                        model=self.llm_model,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    
                    # Extract JSON from response
                    content = response['message']['content']
                    print(f"Received response from LLM")
                    
                    # Parse JSON response
                    metadata = json.loads(content)
                    
                    # Validate the structure
                    if not isinstance(metadata, dict):
                        raise ValueError("Response is not a dictionary")
                    
                    if "table_name" not in metadata or "columns" not in metadata:
                        raise ValueError("Response missing required keys")
                    
                    if not isinstance(metadata["columns"], dict):
                        raise ValueError("Columns should be a dictionary")
                    
                    print(f"Successfully parsed metadata with table_name: {metadata['table_name']}")
                    return metadata
                    
                except Exception as e:
                    print(f"Error with LLM: {str(e)}. Using fallback method.")
                    return self._fallback_metadata_extraction(df, Path(csv_path).stem)
                    
            except Exception as e:
                print(f"Error preparing LLM prompt: {str(e)}. Using fallback method.")
                return self._fallback_metadata_extraction(df, Path(csv_path).stem)
                
        except Exception as e:
            print(f"Error loading CSV: {str(e)}")
            
            # Use fallback method with default name
            return {
                "table_name": Path(csv_path).stem,
                "columns": {"file": "CSV data file"}
            }
    
    def _fallback_metadata_extraction(self, df: pd.DataFrame, table_name: str) -> Dict[str, Any]:
        """
        Fallback method for metadata extraction when LLM fails.
        
        Args:
            df: DataFrame with CSV data
            table_name: Name of the table
            
        Returns:
            Basic metadata with table name and column names
        """
        # Extract column information
        columns = {}
        for col in df.columns:
            clean_col = col.lower().replace(' ', '_')
            # Very simple description - just the column name itself without jargon
            columns[clean_col] = f"{col.replace('_', ' ').title()}"
        
        return {
            "table_name": table_name,
            "columns": columns
        }
    
    def save_metadata_to_chroma(self, user_id: str, table_name: str, 
                               columns: Dict[str, str]) -> str:
        """
        Save table metadata to user-specific ChromaDB collection.
        
        Args:
            user_id: User identifier
            table_name: Name of the table
            columns: Dictionary of column names and descriptions
            
        Returns:
            Document ID of the saved metadata
        """
        # Get the collection for this user
        collection = self._get_user_collection(user_id)
        
        # Create document ID from user_id and table_name
        document_id = f"{table_name}_{user_id}"
        
        # Create document text representation
        column_names = ", ".join(columns.keys())
        document_text = f"Table {table_name} with columns {column_names}"
        
        # Create metadata for document - ensure all values are primitive types
        metadata = {
            "user_id": user_id,
            "table_name": table_name,
            "columns_list": ",".join(list(columns.keys())),  # Convert list to string
        }
        
        # Add column descriptions as individual metadata fields
        for col_name, col_desc in columns.items():
            safe_col_name = f"col_{col_name.replace(' ', '_').replace('.', '_')}"
            metadata[safe_col_name] = str(col_desc)  # Ensure value is string
        
        # Check if document already exists
        try:
            existing = collection.get(ids=[document_id])
            if existing and existing['ids']:
                # Update existing document
                collection.update(
                    ids=[document_id],
                    documents=[document_text],
                    metadatas=[metadata]
                )
            else:
                # Create new document
                collection.add(
                    ids=[document_id],
                    documents=[document_text],
                    metadatas=[metadata]
                )
        except Exception as e:
            print(f"Error while saving to ChromaDB: {e}")
            # Attempt to add as new in case of error
            try:
                # Fallback with even simpler metadata if needed
                simplified_metadata = {
                    "user_id": user_id,
                    "table_name": table_name,
                    "columns_count": str(len(columns))
                }
                collection.add(
                    ids=[document_id],
                    documents=[document_text],
                    metadatas=[simplified_metadata]
                )
            except Exception as e2:
                print(f"Fallback save also failed: {e2}")
                raise
        
        return document_id
    
    def search_relevant_metadata(self, user_id: str, query_text: str) -> Optional[Dict[str, Any]]:
        """
        Search for relevant table metadata based on a user query.
        
        Args:
            user_id: User identifier
            query_text: The natural language query
            
        Returns:
            Most relevant metadata or None if no match found
        """
        try:
            # Get the collection for this user
            collection = self._get_user_collection(user_id)
            
            # Query ChromaDB for relevant documents
            results = collection.query(
                query_texts=[query_text],
                n_results=1,
                where={"user_id": user_id}
            )
            
            if not results['ids'][0]:
                # No results found
                return None
            
            # Get the most relevant metadata
            document_id = results['ids'][0][0]
            chroma_metadata = results['metadatas'][0][0]
            
            # Extract column information from metadata
            columns = []
            column_descriptions = {}
            
            # Process metadata keys to find column information
            for key, value in chroma_metadata.items():
                if key.startswith('col_'):
                    # Extract original column name by removing the 'col_' prefix
                    col_name = key[4:].replace('_', ' ')
                    columns.append(col_name)
                    column_descriptions[col_name] = value
            
            # If no columns were found but we have columns_list
            if not columns and 'columns_list' in chroma_metadata:
                columns = chroma_metadata['columns_list'].split(',')
                for col in columns:
                    column_descriptions[col] = col.replace('_', ' ').title()
            
            # Extract base table name from metadata
            base_table_name = chroma_metadata.get("table_name")
            
            # Construct full table name with user_id suffix
            # PostgreSQL tables are stored as tablename_userid, but metadata may only have the base name
            full_table_name = f"{base_table_name}_{user_id}" if base_table_name else None
            
            return {
                "document_id": document_id,
                "table_name": full_table_name,  # Return full table name with user_id
                "base_table_name": base_table_name,  # Keep base name for reference
                "columns": columns,
                "column_descriptions": column_descriptions
            }
            
        except Exception as e:
            print(f"Error searching relevant metadata: {e}")
            return None
    
    def list_user_tables(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all tables registered for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of table metadata for the user
        """
        try:
            # Get the collection for this user
            collection = self._get_user_collection(user_id)
            
            # Get all documents for the user
            results = collection.get(
                where={"user_id": user_id}
            )
            
            if not results or not results['ids']:
                return []
            
            # Process results into a list of table info
            tables = []
            for i, doc_id in enumerate(results['ids']):
                metadata = results['metadatas'][i]
                tables.append({
                    "document_id": doc_id,
                    "table_name": metadata.get("table_name", "unknown"),
                    "columns": metadata.get("columns", []),
                    "column_count": len(metadata.get("columns", []))
                })
            
            return tables
            
        except Exception as e:
            print(f"Error listing user tables: {e}")
            return [] 