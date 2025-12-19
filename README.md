# ParseQri MCP - CSV Intelligence Suite

<div align="center">

**Natural Language Data Analysis for CSV Files**  
Process, query, and visualize CSV data using plain English powered by AI agents

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13%2B-316192.svg)](https://www.postgresql.org/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 🌟 Overview

ParseQri MCP is a comprehensive data analysis platform that combines the power of Model Context Protocol (MCP) with an intelligent multi-agent system to process and analyze CSV data using natural language. The suite consists of two main components:

- **CSV_MCP** - MCP server exposing data processing tools via standardized protocol
- **CSV_Agent** - Intelligent agent system for natural language to SQL conversion

## 🎯 Key Features

### 🚀 Natural Language Queries
Ask questions in plain English and get instant SQL-backed insights:
- _"Show me the top 10 customers by revenue"_
- _"What's the average loan amount by region?"_
- _"Find all orders from last month with value > $1000"_

### 🔄 Seamless CSV Processing
- **Auto-upload**: Drop CSV files and they're automatically processed
- **Multi-user support**: Isolated data storage per user
- **Smart metadata extraction**: AI-powered schema understanding
- **Type inference**: Automatic data type detection

### 🧠 Intelligent AI Agents
Modular architecture with specialized agents:
- Intent Classification
- Schema Understanding
- SQL Generation & Validation
- Query Execution
- Response Formatting
- Data Visualization
- Query Caching (Redis)

### 📊 Built-in Visualizations
Generate charts and graphs automatically:
- Line charts, bar charts, scatter plots
- Heatmaps, pie charts, histograms
- Advanced statistical visualizations

### ⚡ Performance Optimized
- Redis-based query caching
- ChromaDB metadata indexing
- Smart schema filtering
- Connection pooling

---

## 📦 What's Included

### 🗂️ CSV_MCP Server
Model Context Protocol server that exposes CSV processing capabilities:

**Key Tools:**
- `upload_csv` - Upload and process CSV files
- `query_data` - Execute natural language queries
- `delete_data` - Clean up tables and metadata
- `list_tables` - View available datasets

**Supported Modes:**
- **Stdio Mode** - For Claude Desktop and MCP clients
- **HTTP/SSE Mode** - For remote access and web integration

### 🤖 CSV_Agent System
Multi-agent text-to-SQL processing pipeline:

**Agent Components:**
1. **Data Ingestion Agent** - CSV validation and loading
2. **Schema Understanding Agent** - Database schema extraction
3. **Intent Classification Agent** - Query type detection
4. **SQL Generation Agent** - Natural language → SQL conversion
5. **SQL Validation Agent** - Query correctness verification
6. **Query Execution Agent** - Safe SQL execution
7. **Response Formatting Agent** - Natural language responses
8. **Visualization Agent** - Chart generation
9. **Metadata Indexer Agent** - Semantic metadata storage
10. **Query Cache Agent** - Redis-based caching
11. **PostgreSQL Handler Agent** - Database operations

---

## 🛠️ Installation

### Prerequisites

- **Python 3.8+**
- **PostgreSQL 13+**
- **Ollama** (for LLM capabilities)
- **Redis** (optional, for caching)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/Sonadas21/ParseQri_MCP.git
   cd ParseQri_MCP
   ```

2. **Set up PostgreSQL**
   ```bash
   # Create database
   createdb parseqri
   
   # Or using psql
   psql -U postgres
   CREATE DATABASE parseqri;
   ```

3. **Install CSV_Agent dependencies**
   ```bash
   cd CSV_Agent
   pip install -r requirements.txt
   ```

4. **Install CSV_MCP dependencies**
   ```bash
   cd ../CSV_MCP
   pip install -r requirements.txt
   ```

5. **Configure database connection**
   
   Update `CSV_Agent/config.json` with your PostgreSQL credentials:
   ```json
   {
     "agents": {
       "postgres_handler": {
         "params": {
           "db_url": "postgresql://username:password@localhost:5432/parseqri"
         }
       }
     }
   }
   ```

6. **Start Ollama**
   ```bash
   ollama serve
   
   # Pull required models
   ollama pull PetrosStav/gemma3-tools:4b
   ollama pull llama3.1:8b-instruct-q4_K_M
   ollama pull qwen3:4b
   ```

7. **Start Redis** (optional, for caching)
   ```bash
   # Using Docker
   docker run -d -p 6379:6379 redis:latest
   
   # Or use the provided script
   cd CSV_Agent
   ./redis-docker.sh  # Linux/Mac
   redis-docker.bat   # Windows
   ```

---

## 🚀 Usage

### Using CSV_MCP Server

#### For Claude Desktop (Stdio Mode)

1. **Configure Claude Desktop**
   
   Add to your Claude Desktop config:
   ```json
   {
     "mcpServers": {
       "csv-mcp": {
         "command": "python",
         "args": ["d:/Projects/C2CAS_Projects/Deployable/ParseQri_MCP/CSV_MCP/server.py"],
         "env": {}
       }
     }
   }
   ```

2. **Restart Claude Desktop**

3. **Use the tools in conversation**
   ```
   User: Upload this CSV file: d:/data/customers.csv
   Claude: [Uses upload_csv tool]
   
   User: Show me the top 5 customers by revenue
   Claude: [Uses query_data tool]
   ```

#### HTTP/SSE Mode (Remote Access)

```bash
cd CSV_MCP

# Start HTTP server
python server.py --http --host 0.0.0.0 --port 8000

# Server now available at:
# http://localhost:8000
# SSE endpoint: http://localhost:8000/sse
```

#### Testing with MCP Inspector

```bash
cd CSV_MCP
npx @modelcontextprotocol/inspector python server.py
```

### Using CSV_Agent Directly

#### Simple Query Example

```bash
cd CSV_Agent
python main.py "What is the average loan amount?"
```

#### With Automatic CSV Processing

```bash
# Place CSV files in uploads/ folder
cp mydata.csv uploads/

# Run query (auto-processes new files)
python main.py "Show me all records from mydata"
```

#### File Watcher Mode

```bash
# Continuously monitor uploads/ folder
python watch_data_folder.py

# Add files to uploads/ - they'll be processed automatically
```

---

## 📖 Example Workflows

### Workflow 1: Upload and Query

```python
# Using CSV_MCP tools in Claude or other MCP client

# 1. Upload CSV
upload_csv(
    file_path="d:/data/sales_2024.csv",
    user_id="john_doe",
    table_name="sales"
)

# 2. Query the data
query_data(
    query="What were the total sales by region?",
    user_id="john_doe",
    table_name="sales"
)

# 3. List all tables
list_tables(user_id="john_doe")

# 4. Delete when done
delete_data(
    user_id="john_doe",
    table_name="sales",
    confirm=true
)
```

### Workflow 2: Direct Agent Usage

```python
from core.orchestrator import Orchestrator

# Initialize
config_path = "CSV_Agent/config.json"
orchestrator = Orchestrator(config_path)

# Upload CSV
result = orchestrator.upload_csv(
    file_path="sales.csv",
    user_id="analyst_1",
    table_name="monthly_sales"
)

# Query
response = orchestrator.process_query(
    query="Show me monthly trends",
    user_id="analyst_1",
    table_name="monthly_sales"
)

print(response['natural_language_response'])
print(response['sql_query'])
```

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        MCP Clients                          │
│              (Claude Desktop, Custom Apps)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      CSV_MCP Server                         │
│                  (FastMCP Protocol)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    CSV_Agent System                         │
│                    (Orchestrator)                           │
└─────┬───────────────────────────────────────────────────┬───┘
      │                                                   │
      ▼                                                   ▼
┌─────────────────┐                           ┌──────────────────┐
│  Agent Pipeline │                           │  Data Stores     │
├─────────────────┤                           ├──────────────────┤
│ • Intent        │                           │ • PostgreSQL     │
│ • Schema        │◄──────────────────────────│   (CSV Data)     │
│ • SQL Gen       │                           │                  │
│ • Validation    │                           │ • ChromaDB       │
│ • Execution     │◄──────────────────────────│   (Metadata)     │
│ • Formatting    │                           │                  │
│ • Visualization │                           │ • Redis          │
│ • Caching       │◄──────────────────────────│   (Query Cache)  │
└─────────────────┘                           └──────────────────┘
```

### Data Processing Flow

```
CSV Upload Flow:
┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────────┐
│   CSV    │───▶│  Validation  │───▶│   Metadata   │───▶│PostgreSQL │
│   File   │    │  & Parsing   │    │  Extraction  │    │  Storage  │
└──────────┘    └──────────────┘    └──────┬───────┘    └───────────┘
                                            │
                                            ▼
                                     ┌──────────────┐
                                     │  ChromaDB    │
                                     │  Indexing    │
                                     └──────────────┘

Query Processing Flow:
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Natural  │───▶│  Intent  │───▶│  Schema  │───▶│   SQL    │───▶│  Query   │
│ Language │    │Classifier│    │  Filter  │    │Generator │    │Execution │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └────┬─────┘
                                                                       │
                   ┌───────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│ Response │◄───│  Format  │◄───│   Cache  │
│ to User  │    │  Results │    │  Check   │
└──────────┘    └──────────┘    └──────────┘
```

---

## ⚙️ Configuration

### CSV_Agent Configuration

Edit `CSV_Agent/config.json`:

```json
{
  "agents": {
    "postgres_handler": {
      "params": {
        "db_url": "postgresql://user:pass@host:5432/dbname",
        "schema": "public"
      }
    },
    "query_cache": {
      "params": {
        "redis_host": "localhost",
        "redis_port": 6379,
        "ttl_seconds": 86400,
        "use_fallback": true
      }
    },
    "metadata_indexer": {
      "params": {
        "llm_model": "PetrosStav/gemma3-tools:4b",
        "api_base": "http://localhost:11434",
        "chroma_persist_dir": "../data/db_storage"
      }
    }
  }
}
```

### LLM Models Configuration

The system uses different Ollama models for specific tasks:

| Agent | Model | Purpose |
|-------|-------|---------|
| Intent Classification | `gemma3-tools:4b` | Fast intent detection |
| Schema Understanding | `gemma3-tools:4b` | Schema analysis |
| SQL Generation | `llama3.1:8b` | Complex SQL creation |
| SQL Validation | `llama3.1:8b` | Query verification |
| Response Formatting | `qwen3:4b` | Natural language responses |
| Visualization | `gemma3-tools:4b` | Chart generation |

### Multi-User Data Isolation

Each user gets isolated storage:

```
User: john_doe
├── PostgreSQL Tables: sales_john_doe, customers_john_doe
├── ChromaDB Collection: john_doe_metadata
└── Metadata Files: db_storage/john_doe/
```

---

## 🧪 Testing & Development

### Run Tests

```bash
cd CSV_Agent
python -m pytest tests/
```

### Test Individual Agents

```bash
# Test SQL generation
python simplified_query.py "show me all customers"

# Test cache
python inspect_cache.py

# Clear databases
python clear_databases.py
```

### Debug Mode

Enable detailed logging in `config.json`:

```json
{
  "logging": {
    "level": "DEBUG",
    "file": "textsql.log"
  }
}
```

---

## 📚 Documentation

Each component has detailed documentation:

- **[CSV_MCP Documentation](CSV_MCP/README.md)** - MCP server setup and API
- **[CSV_MCP Quickstart](CSV_MCP/QUICKSTART.md)** - Quick start guide
- **[CSV_MCP Troubleshooting](CSV_MCP/TROUBLESHOOTING.md)** - Common issues
- **[CSV_Agent Documentation](CSV_Agent/README.md)** - Agent system details
- **[Multi-User Guide](CSV_Agent/README_MULTI_USER.md)** - Multi-user setup
- **[Redis Cache Guide](CSV_Agent/REDIS_CACHE_README.md)** - Caching configuration

---

## 🐛 Troubleshooting

### Common Issues

#### PostgreSQL Connection Failed
```bash
# Check PostgreSQL is running
pg_isready

# Verify credentials
psql -U username -d parseqri

# Update config.json with correct credentials
```

#### Ollama Not Found
```bash
# Start Ollama service
ollama serve

# Verify models are available
ollama list

# Pull missing models
ollama pull PetrosStav/gemma3-tools:4b
```

#### ChromaDB Permission Errors
```bash
# Ensure write permissions
chmod -R 755 data/db_storage

# Or on Windows, check folder permissions in Properties
```

#### CSV Upload Fails
- Verify file path is absolute
- Check CSV encoding (UTF-8 recommended)
- Ensure CSV has headers
- Check for special characters in column names

#### Query Returns Empty Results
- Use `list_tables` to verify table exists
- Ensure `user_id` matches upload user
- Don't include user_id suffix in table_name
- Check query syntax

---

## 🔒 Security Considerations

- **SQL Injection Prevention**: All queries are validated before execution
- **User Isolation**: Each user's data is isolated using prefixed tables
- **Parameterized Queries**: Agent uses prepared statements
- **Input Validation**: CSV files are validated before processing
- **Access Control**: Configure database users with minimal required permissions

---

## 🚦 Performance Tips

1. **Enable Redis Caching**: Significantly speeds up repeated queries
   ```bash
   docker run -d -p 6379:6379 redis:latest
   ```

2. **Optimize PostgreSQL**: Add indexes for frequently queried columns
   ```sql
   CREATE INDEX idx_user_column ON table_name(column_name);
   ```

3. **Use Appropriate LLM Models**: Balance speed vs. accuracy
   - Fast: `gemma3-tools:4b`
   - Accurate: `llama3.1:8b`

4. **Batch Processing**: Upload multiple CSVs at once

5. **ChromaDB Maintenance**: Periodically clean old metadata
   ```bash
   python clear_databases.py
   ```

---

## 🗺️ Roadmap

- [ ] **Database Agent** - Direct MySQL, PostgreSQL, MSSQL connections
- [ ] **Excel Support** - .xlsx file processing
- [ ] **Advanced Analytics** - Statistical analysis agents
- [ ] **Real-time Streaming** - Live data processing
- [ ] **Web UI** - Browser-based interface
- [ ] **API Gateway** - REST API for integration
- [ ] **Containerization** - Full Docker Compose setup
- [ ] **Cloud Deployment** - AWS/Azure/GCP templates

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Authors

**ParseQri Development Team**
- Sona Das - *Initial work* - [Sonadas21](https://github.com/Sonadas21)

---

## 🙏 Acknowledgments

- **Model Context Protocol** - For the standardized AI integration protocol
- **Ollama** - For local LLM inference
- **ChromaDB** - For vector database capabilities
- **FastMCP** - For the Python MCP server framework
- **PostgreSQL Community** - For the robust database system

---

## 📞 Support

For issues, questions, or feature requests:

- **GitHub Issues**: [Report a bug](https://github.com/Sonadas21/ParseQri_MCP/issues)
- **Email**: dass21656@gmail.com
- **Documentation**: Check the docs/ folder for detailed guides

---

<div align="center">

**Made with ❤️ by the ParseQri Team**

⭐ Star us on GitHub if this project helped you!

</div>
