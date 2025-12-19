# TextToSQL Agent

A modular text-to-SQL system with visualization capabilities. This system breaks down the text-to-SQL process into separate agent components, each responsible for a specific part of the pipeline.

## Overview

TextToSQL_Agent converts natural language queries into SQL, executes them on a database, and returns formatted results or visualizations. The system is designed to be modular, with separate agents handling different aspects of the process.

## Features

- Natural language to SQL conversion
- Query validation and correction
- Result formatting in natural language
- Data visualization
- Query caching for improved performance
- Data preprocessing and cleaning
- Schema understanding and management
- **Automatic CSV file processing** from a data folder

## Architecture

The system is built around a modular agent-based architecture:

1. **Data Ingestion Agent**: Loads CSV data and converts to SQLite
2. **Schema Understanding Agent**: Extracts database schema information
3. **Intent Classification Agent**: Determines if visualization or SQL is needed
4. **SQL Generation Agent**: Converts natural language to SQL
5. **SQL Validation Agent**: Validates and fixes SQL queries
6. **Query Execution Agent**: Executes SQL queries
7. **Response Formatting Agent**: Formats results as natural language
8. **Visualization Agent**: Creates data visualizations
9. **Data Preprocessing Agent**: Cleans and preprocesses data
10. **Query Cache Agent**: Caches queries for faster responses
11. **Schema Management Agent**: Manages schema metadata
12. **Advanced Visualization Agent**: Creates complex visualizations

## Usage

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd TextToSQL_Agent
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

### Running Queries

To run a natural language query:

```bash
python main.py "What is the average loan amount?"
```

### Using the Data Folder

The system now includes an automated data folder feature:

1. **Add CSV files** - Place your CSV files in the `data/` folder
2. **Automatic processing** - Files are processed automatically when you run `main.py`
3. **Continuous monitoring** - Run the dedicated watcher to process files as they're added:

```bash
python watch_data_folder.py
```

By default, the system will:
- Use the filename as the table name if appropriate
- Clean column names for SQL compatibility
- Load data into the configured SQLite database

For more control, use command-line options:
```bash
python watch_data_folder.py --data-folder custom_path --interval 10
```

## Configuration

The system is configured through `config.json`. You can modify this file to:

- Change LLM models for specific agents
- Set database connection information
- Configure logging options
- Add new agents
- Configure the **data folder location** and database settings:
```json
"database": {
    "default_db_name": "loan_db.db",
    "default_table_name": "loan_dt",
    "data_folder": "custom_data_path"
}
```

## Requirements

- Python 3.8+
- SQLite
- pandas
- ollama (for LLM access)
- plotly
- matplotlib
- seaborn

## LLM Models Used

- Intent Classification: llama3.1 (via Ollama)
- Schema Understanding: mistral
- SQL Generation: qwen2.5:3b
- SQL Validation: deepseek-r1:1.5b
- Response Formatting: mistral
- Visualization: llama3.1

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 