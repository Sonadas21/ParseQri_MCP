import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Any, Optional
from models.data_models import QueryContext, AgentResponse

class AdvancedVisualizationAgent:
    """
    Agent responsible for creating advanced visualizations.
    Provides recommendations and supports multiple visualization libraries.
    """
    
    def __init__(self):
        """Initialize the Advanced Visualization Agent."""
        self.available_libraries = {
            'plotly': px,
            'matplotlib': plt,
            'seaborn': sns
        }
        self.df = None
        
    def process(self, context: QueryContext) -> AgentResponse:
        """Process the query context to create advanced visualizations."""
        try:
            # If we don't have a dataframe to visualize, assume it's not needed
            if not hasattr(context, 'query_results') or context.query_results is None:
                return AgentResponse(
                    success=True,
                    message="No data provided for visualization",
                    data={}
                )
                
            self.df = context.query_results
            
            # Determine visualization type based on data
            visualization_info = self.recommend_visualization_type(self.df)
            
            # Create visualization
            fig = self.create_visualization(
                visualization_info['type'],
                visualization_info['data'],
                visualization_info.get('library', 'plotly')
            )
            
            if fig is None:
                return AgentResponse(
                    success=False,
                    message="Failed to create visualization"
                )
                
            # Convert figure to data for transmission
            if hasattr(fig, 'to_dict'):
                # Plotly figure
                fig_data = fig.to_dict()
            else:
                # Matplotlib/Seaborn figure - convert to string representation
                fig_data = str(fig)
                
            return AgentResponse(
                success=True,
                message="Advanced visualization created successfully",
                data={
                    "visualization_data": {
                        "type": visualization_info['type'],
                        "lib": visualization_info.get('library', 'plotly'),
                        "fig_data": fig_data
                    }
                }
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"Error in advanced visualization: {str(e)}"
            )
            
    def recommend_visualization_type(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Recommend visualization type based on dataframe characteristics.
        
        Args:
            df: DataFrame to visualize
            
        Returns:
            Dictionary with visualization recommendations
        """
        # Get numeric and categorical columns
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        # Simple heuristics for visualization type
        if len(numeric_cols) == 0:
            # No numeric columns, use bar chart for categorical data
            result = {
                'type': 'bar',
                'data': {
                    'x': categorical_cols[0] if categorical_cols else df.columns[0],
                    'y': None
                },
                'library': 'plotly'
            }
        elif len(numeric_cols) == 1 and len(categorical_cols) >= 1:
            # One numeric and at least one categorical, use grouped bar
            result = {
                'type': 'bar',
                'data': {
                    'x': categorical_cols[0],
                    'y': numeric_cols[0],
                    'color': categorical_cols[1] if len(categorical_cols) > 1 else None
                },
                'library': 'plotly'
            }
        elif len(numeric_cols) >= 2:
            # Multiple numeric columns, use scatter plot
            result = {
                'type': 'scatter',
                'data': {
                    'x': numeric_cols[0],
                    'y': numeric_cols[1],
                    'color': categorical_cols[0] if categorical_cols else None,
                    'size': numeric_cols[2] if len(numeric_cols) > 2 else None
                },
                'library': 'plotly'
            }
        else:
            # Default to histogram of first column
            result = {
                'type': 'histogram',
                'data': {
                    'x': df.columns[0]
                },
                'library': 'plotly'
            }
            
        return result
        
    def create_visualization(self, viz_type: str, data: Dict[str, Any], library: str = 'plotly') -> Any:
        """
        Create visualization using specified library.
        
        Args:
            viz_type: Type of visualization (e.g., 'scatter', 'bar')
            data: Data specifications for the visualization
            library: Library to use for visualization
            
        Returns:
            Figure object from the respective library
        """
        lib = self.available_libraries.get(library)
        if not lib:
            raise ValueError(f"Unsupported visualization library: {library}")
            
        # Handle library-specific visualizations
        if library == 'plotly':
            return self._create_plotly_viz(viz_type, data)
        elif library == 'matplotlib':
            return self._create_matplotlib_viz(viz_type, data)
        elif library == 'seaborn':
            return self._create_seaborn_viz(viz_type, data)
        else:
            raise ValueError(f"Unsupported visualization library: {library}")
            
    def _create_plotly_viz(self, viz_type: str, data: Dict[str, Any]) -> Any:
        """Create visualization using Plotly."""
        if viz_type == 'histogram':
            return px.histogram(self.df, x=data['x'])
        elif viz_type == 'bar':
            return px.bar(self.df, x=data['x'], y=data['y'], color=data.get('color'))
        elif viz_type == 'scatter':
            return px.scatter(self.df, x=data['x'], y=data['y'], color=data.get('color'), size=data.get('size'))
        elif viz_type == 'line':
            return px.line(self.df, x=data['x'], y=data['y'], color=data.get('color'))
        elif viz_type == 'pie':
            return px.pie(self.df, names=data['names'], values=data['values'])
        else:
            # Default to table
            return go.Figure(data=[go.Table(
                header=dict(values=list(self.df.columns)),
                cells=dict(values=[self.df[col] for col in self.df.columns])
            )])
            
    def _create_matplotlib_viz(self, viz_type: str, data: Dict[str, Any]) -> Any:
        """Create visualization using Matplotlib."""
        fig, ax = plt.subplots()
        
        if viz_type == 'histogram':
            ax.hist(self.df[data['x']])
            ax.set_xlabel(data['x'])
        elif viz_type == 'bar':
            self.df.plot.bar(x=data['x'], y=data['y'], ax=ax)
        elif viz_type == 'scatter':
            ax.scatter(self.df[data['x']], self.df[data['y']])
            ax.set_xlabel(data['x'])
            ax.set_ylabel(data['y'])
        elif viz_type == 'line':
            self.df.plot.line(x=data['x'], y=data['y'], ax=ax)
        else:
            # Default to a simple plot
            self.df.plot(ax=ax)
            
        return fig
        
    def _create_seaborn_viz(self, viz_type: str, data: Dict[str, Any]) -> Any:
        """Create visualization using Seaborn."""
        if viz_type == 'histogram':
            return sns.histplot(data=self.df, x=data['x'])
        elif viz_type == 'bar':
            return sns.barplot(data=self.df, x=data['x'], y=data['y'], hue=data.get('color'))
        elif viz_type == 'scatter':
            return sns.scatterplot(data=self.df, x=data['x'], y=data['y'], hue=data.get('color'), size=data.get('size'))
        elif viz_type == 'line':
            return sns.lineplot(data=self.df, x=data['x'], y=data['y'], hue=data.get('color'))
        else:
            # Default to pairplot for exploratory analysis
            return sns.pairplot(self.df) 