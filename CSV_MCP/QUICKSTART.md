# CSV MCP Server - Quick Start Guide

## Super Simple Usage

No need for user IDs or complex parameters! Just use these simple commands:

### 1. **Upload a CSV File**

```json
{
  "file_path": "d:/data/customers.csv"
}
```

That's it! The file uploads automatically with a default user.

**With custom table name:**
```json
{
  "file_path": "d:/data/customers.csv",
  "table_name": "my_customers"
}
```

### 2. **Ask Questions** (Natural Language Query)

**Simple - No table name needed!**
```json
{
  "query": "show me top 10 rows"
}
```

The system **automatically finds** the right table using semantic search! 🎯

**Or specify a table explicitly:**
```json
{
  "query": "show me top 10 rows",
  "table_name": "customers"
}
```

**You'll get back:**
- `answer`: Natural language response from the LLM (e.g., "Here are the top 10 customers...")
- `results`: Raw data as JSON
- `sql_query`: The generated SQL
- `row_count`: Number of rows

**More examples:**
- `"show all customers from New York"`  ← Auto-finds "customers" table
- `"what's the average age?"`  ← Searches metadata to find right table
- `"count total records"`
- `"find customers with revenue over 1000", table_name="sales"`  ← Explicit table

### 3. **List Your Tables**

```json
{}
```

Yes, just empty! It shows all your uploaded tables.

### 4. **Delete a Table**

```json
{
  "table_name": "customers",
  "confirm": true
}
```

⚠️ **Warning**: This permanently deletes data!

---

## Getting File Paths (Windows)

### Method 1: Drag and Drop to Terminal
1. Open your PowerShell/Terminal
2. Drag the CSV file from File Explorer into the terminal
3. The full path appears automatically!
4. Copy and paste it into the tool

### Method 2: Copy Path from File Explorer
1. Right-click the CSV file
2. Hold `Shift` and click "Copy as path"
3. Paste directly

### Method 3: Type it
```
d:\Projects\MyData\file.csv
```

---

## Complete Examples

### Upload → Query → Delete Flow

**Step 1: Upload**
```json
{
  "file_path": "d:/sales/2024_sales.csv"
}
```

**Response:**
```json
{
  "success": true,
  "table_name": "2024_sales_default_user",
  "message": "CSV uploaded successfully"
}
```

**Step 2: List Tables**
```json
{}
```

**Response:**
```json
{
  "success": true,
  "tables": ["2024_sales"],
  "count": 1
}
```

**Step 3: Query**
```json
{
  "query": "show total sales by month",
  "table_name": "2024_sales"
}
```

**Step 4: Delete (when done)**
```json
{
  "table_name": "2024_sales",
  "confirm": true
}
```

---

## Advanced: Multi-User Support (Optional)

If you want to isolate data by user, you can still provide `user_id`:

```json
{
  "file_path": "d:/data/customers.csv",
  "user_id": "john_doe"
}
```

Then use the same `user_id` for queries:

```json
{
  "query": "show all",
  "table_name": "customers",
  "user_id": "john_doe"
}
```

But for most cases, just stick with the defaults!

---

## Tips

💡 **Don't forget `confirm: true` when deleting** - it's a safety feature!

💡 **Table names auto-generated** from your CSV filename if not specified

💡 **Ask questions naturally** - the AI understands plain English

💡 **No setup needed** - just upload and query immediately
