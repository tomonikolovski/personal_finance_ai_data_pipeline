# MCP Transaction Analyzer

This is an MCP (Model Context Protocol) server that provides AI-powered financial transaction analysis capabilities. It connects to your existing MinIO + Spark data pipeline to enable natural language queries about your financial data.

## Features

### Tools
- **analyze_spending**: Analyze spending patterns with optional filters
- **categorize_transactions**: Automatically categorize transactions and show spending by category
- **detect_anomalies**: Find unusual transactions above a threshold
- **compare_periods**: Compare spending between two time periods

### Resources
- **transaction://schema**: Get the schema of transaction data
- **transaction://stats**: Get basic statistics about the transaction dataset

## Usage with Claude Desktop

1. Add this to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "transaction-analyzer": {
      "command": "docker",
      "args": ["exec", "mcp-transaction-analyzer", "python", "server.py"]
    }
  }
}
```

2. Ask Claude questions like:
   - "How much did I spend on food last month?"
   - "Show me my spending by category"
   - "Find any transactions over $500"
   - "Compare my spending this month vs last month"

## Example Queries

### Analyze Spending
```
Analyze my spending from April 2024 to May 2024, focusing on entertainment
```

### Categorize Transactions
```
Show me how my spending breaks down by category for the last 3 months
```

### Detect Anomalies
```
Find any unusual transactions over $300 in the past year
```

### Compare Periods
```
Compare my spending between January 2024 and February 2024 vs March 2024 and April 2024
```

## Data Schema

The transaction data includes:
- Account Type
- Account Number
- Transaction Date
- Cheque Number
- Description 1 & 2
- CAD$ (amount in Canadian dollars)
- USD$ (amount in US dollars)

## Architecture

- **MCP Protocol**: Uses Model Context Protocol for AI integration
- **Spark Integration**: Leverages your existing Spark cluster for distributed processing
- **MinIO Connection**: Reads transaction data from your S3-compatible storage
- **Docker Compose**: Runs as part of your docker-compose setup using the mounted JDK 22 from spark-client

## Development

To run locally (outside Docker):

```bash
cd mcp_transaction_analyzer
pip install -r requirements.txt
export MINIO_ACCESS_KEY=minio
export MINIO_SECRET_KEY=minio123
export MINIO_ENDPOINT=http://localhost:9000
python server.py
```

The MCP server is also included in the main docker-compose.yml and will start automatically with the rest of the pipeline.

## Integration with Existing Pipeline

This MCP server integrates seamlessly with your existing:
- Kafka streaming pipeline
- MinIO object storage
- Apache Spark cluster
- FastAPI backend

It provides an additional AI interface for data analysis without disrupting your current workflow.