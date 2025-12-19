import pandas as pd
from typing import Dict, Any, List, Optional
from models.data_models import QueryContext, AgentResponse

class DataPreprocessingAgent:
    """
    Agent responsible for preprocessing data before analysis.
    Handles data type detection, cleaning, and outlier handling.
    """
    
    def __init__(self):
        """Initialize the Data Preprocessing Agent."""
        self.data_types = {}
        self.cleaning_stats = {}
        
    def process(self, context: QueryContext) -> AgentResponse:
        """Process the query context to preprocess data."""
        try:
            # If we don't have a dataframe to process, assume it's already been done
            if not hasattr(context, 'dataframe') or context.dataframe is None:
                return AgentResponse(
                    success=True,
                    message="No dataframe provided, skipping preprocessing",
                    data={}
                )
                
            df = context.dataframe
            
            # Detect data types
            self.data_types = self.detect_data_types(df)
            
            # Clean the data
            cleaned_df = self.clean_data(df)
            
            return AgentResponse(
                success=True,
                message="Data preprocessing completed successfully",
                data={
                    "preprocessed_dataframe": cleaned_df,
                    "data_types": self.data_types,
                    "cleaning_stats": self.cleaning_stats
                }
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Error in data preprocessing: {str(e)}"
            )
            
    def detect_data_types(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Automatically detect data types for each column.
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            Dictionary mapping column names to detected data types
        """
        data_types = {}
        
        for column in df.columns:
            try:
                # Check for datetime with specific format parsing
                if any(str(x).count('-') >= 2 for x in df[column].dropna()):
                    try:
                        pd.to_datetime(df[column].dropna(), format='%Y-%m-%d', errors='raise')
                        data_types[column] = 'datetime'
                        continue
                    except:
                        pass
                        
                # Check for numeric
                if pd.api.types.is_numeric_dtype(df[column]):
                    data_types[column] = 'numeric'
                else:
                    data_types[column] = 'text'
            except Exception as e:
                print(f"Warning: Error detecting type for column {column}: {str(e)}")
                data_types[column] = 'text'
                
        return data_types
        
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean data by handling missing values and outliers.
        
        Args:
            df: DataFrame to clean
            
        Returns:
            Cleaned DataFrame
        """
        cleaned_df = df.copy()
        self.cleaning_stats = {
            "missing_values": {},
            "outliers": {}
        }
        
        for column in cleaned_df.columns:
            # Handle missing values
            missing_count = cleaned_df[column].isnull().sum()
            if missing_count > 0:
                self.cleaning_stats["missing_values"][column] = missing_count
                
                if self.data_types.get(column) == 'numeric':
                    # Use pandas fillna directly on the dataframe
                    cleaned_df[column] = cleaned_df[column].fillna(cleaned_df[column].median())
                else:
                    # Handle mode more safely
                    mode_value = cleaned_df[column].mode()
                    if not mode_value.empty:
                        cleaned_df[column] = cleaned_df[column].fillna(mode_value.iloc[0])
                    else:
                        cleaned_df[column] = cleaned_df[column].fillna('')
            
            # Handle outliers for numeric columns
            if self.data_types.get(column) == 'numeric':
                try:
                    Q1 = cleaned_df[column].quantile(0.25)
                    Q3 = cleaned_df[column].quantile(0.75)
                    IQR = Q3 - Q1
                    
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR
                    
                    # Count outliers
                    outlier_mask = (cleaned_df[column] < lower_bound) | (cleaned_df[column] > upper_bound)
                    outlier_count = outlier_mask.sum()
                    
                    if outlier_count > 0:
                        self.cleaning_stats["outliers"][column] = outlier_count
                        # Clip outliers
                        cleaned_df[column] = cleaned_df[column].clip(lower=lower_bound, upper=upper_bound)
                        
                except Exception as e:
                    print(f"Warning: Could not process outliers for column {column}: {str(e)}")
                    
        return cleaned_df 