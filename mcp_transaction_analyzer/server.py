#!/usr/bin/env python3
"""
MCP Server for Transaction Analysis Domain

This MCP server provides AI-powered financial transaction analysis capabilities
by connecting to the existing MinIO + Spark data pipeline.
"""

import asyncio
import os
from typing import Any, Optional

from mcp.server.lowlevel import Server

# Initialize MCP server
server = Server("transaction-analyzer")

# Global variables for connections
spark: Optional["SparkSession"] = None
s3_client = None

def init_spark():
    """Initialize Spark session with MinIO configuration"""
    global spark
    if spark is None:
        try:
            import sys
            from pyspark.sql import SparkSession
            from pyspark.sql.functions import col, sum as spark_sum, count, avg, max, min

            # Set environment variables if not already set
            if 'SPARK_HOME' not in os.environ:
                # Try to find Spark in common locations
                possible_spark_homes = [
                    '/opt/spark/spark-3.5.1-bin-hadoop3',
                    '/usr/local/spark',
                    os.path.join(os.path.dirname(__file__), '..', 'spark-client', 'spark-3.5.1-bin-hadoop3')
                ]
                for spark_home in possible_spark_homes:
                    if os.path.exists(spark_home):
                        os.environ['SPARK_HOME'] = spark_home
                        break

            if 'JAVA_HOME' not in os.environ:
                # Try to find Java - prefer system Java over potentially broken downloaded ones
                import subprocess
                try:
                    java_home = subprocess.check_output(['java', '-XshowSettings:properties', '-version'], stderr=subprocess.STDOUT, text=True)
                    for line in java_home.split('\n'):
                        if 'java.home' in line:
                            java_home_path = line.split('=')[1].strip()
                            os.environ['JAVA_HOME'] = java_home_path
                            print(f"Using system JAVA_HOME: {java_home_path}", file=os.sys.stderr)
                            break
                except Exception as e:
                    print(f"Could not determine JAVA_HOME: {e}", file=os.sys.stderr)

            # Set PySpark environment variables
            if 'PYSPARK_PYTHON' not in os.environ:
                os.environ['PYSPARK_PYTHON'] = sys.executable
            if 'PYSPARK_DRIVER_PYTHON' not in os.environ:
                os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable

            # Set Java options to avoid some common issues
            if 'JAVA_OPTS' not in os.environ:
                os.environ['JAVA_OPTS'] = '-Xmx1g --add-opens java.base/javax.security.auth=ALL-UNNAMED --add-opens java.base/java.lang=ALL-UNNAMED --add-opens java.base/java.util=ALL-UNNAMED'

            spark = SparkSession.builder \
                .appName("TransactionAnalyzer") \
                .config("spark.hadoop.fs.s3a.access.key", os.getenv("MINIO_ACCESS_KEY", "minio")) \
                .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_SECRET_KEY", "minio123")) \
                .config("spark.hadoop.fs.s3a.endpoint", os.getenv("MINIO_ENDPOINT", "http://minio:9000")) \
                .config("spark.hadoop.fs.s3a.path.style.access", "true") \
                .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
                .config("spark.hadoop.security.authentication", "simple") \
                .config("spark.hadoop.security.authorization", "false") \
                .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
                .config("spark.ui.enabled", "false") \
                .config("spark.master", os.getenv("SPARK_MASTER_URL", "local[*]")) \
                .config("spark.driver.memory", "512m") \
                .config("spark.executor.memory", "512m") \
                .config("spark.sql.adaptive.enabled", "false") \
                .config("spark.driver.extraJavaOptions", "--add-opens java.base/javax.security.auth=ALL-UNNAMED") \
                .config("spark.executor.extraJavaOptions", "--add-opens java.base/javax.security.auth=ALL-UNNAMED") \
                .getOrCreate()

            # Test the connection
            spark.sql("SELECT 1").collect()
            print("Spark session initialized successfully", file=os.sys.stderr)

        except Exception as e:
            print(f"Warning: Spark initialization failed: {e}", file=os.sys.stderr)
            print("Server will continue without Spark functionality. Spark-dependent tools will return error messages.", file=os.sys.stderr)
            spark = None
    return spark

def init_s3():
    """Initialize S3 client for MinIO"""
    global s3_client
    if s3_client is None:
        import boto3
        s3_client = boto3.client(
            's3',
            endpoint_url=os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
            aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minio"),
            aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minio123"),
            region_name='us-east-1'
        )
    return s3_client

def load_transaction_data(bucket: str = "bucket1", prefix: str = "topic1/partition=0/", date_from: str = None, date_to: str = None) -> Any:
    """Load transaction data from MinIO into Spark DataFrame, optionally filtered by date range"""
    spark_session = init_spark()
    if spark_session is None:
        raise Exception("Spark is not available. Please check the server logs for initialization errors.")

    s3_path = f"s3a://{bucket}/{prefix}*.json"

    try:
        df = spark_session.read.json(s3_path)
        
        # Apply date filters if provided to limit data loaded
        if date_from:
            df = df.filter(f"`Transaction Date` >= '{date_from}'")
        if date_to:
            df = df.filter(f"`Transaction Date` <= '{date_to}'")
        
        return df
    except Exception as e:
        raise Exception(f"Failed to load data from {s3_path}: {str(e)}")

@server.list_tools()
async def list_tools():
    """List available tools"""
    from mcp.types import Tool
    return [
        Tool(
            name="analyze_spending",
            description="Analyze spending patterns from transaction data",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Category to filter by (food, entertainment, transport, shopping, utilities)"},
                    "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "account_type": {"type": "string", "description": "Account type filter"}
                }
            }
        ),
        Tool(
            name="categorize_transactions",
            description="Automatically categorize transactions and show spending by category",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "min_amount": {"type": "number", "description": "Minimum transaction amount"}
                }
            }
        ),
        Tool(
            name="detect_anomalies",
            description="Detect unusual transactions that might be anomalies",
            inputSchema={
                "type": "object",
                "properties": {
                    "threshold": {"type": "number", "description": "Amount threshold for anomaly detection", "default": 500},
                    "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"}
                }
            }
        ),
        Tool(
            name="compare_periods",
            description="Compare spending between two time periods",
            inputSchema={
                "type": "object",
                "required": ["period1_start", "period1_end", "period2_start", "period2_end"],
                "properties": {
                    "period1_start": {"type": "string", "description": "Start date for period 1 (YYYY-MM-DD)"},
                    "period1_end": {"type": "string", "description": "End date for period 1 (YYYY-MM-DD)"},
                    "period2_start": {"type": "string", "description": "Start date for period 2 (YYYY-MM-DD)"},
                    "period2_end": {"type": "string", "description": "End date for period 2 (YYYY-MM-DD)"}
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool calls"""
    from mcp.types import TextContent
    try:
        if name == "analyze_spending":
            return await handle_analyze_spending(arguments)
        elif name == "categorize_transactions":
            return await handle_categorize_transactions(arguments)
        elif name == "detect_anomalies":
            return await handle_detect_anomalies(arguments)
        elif name == "compare_periods":
            return await handle_compare_periods(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error calling tool {name}: {str(e)}")]

async def handle_analyze_spending(args: dict):
    """Handle analyze_spending tool"""
    from mcp.types import TextContent
    from pyspark.sql.functions import col, sum as spark_sum, count, avg, max
    try:
        df = load_transaction_data()

        # Apply filters
        if args.get("category"):
            category = args["category"].lower()
            category_keywords = {
                'food': ['restaurant', 'grocery', 'food', 'cafe', 'coffee'],
                'entertainment': ['movie', 'game', 'music', 'theater'],
                'transport': ['gas', 'uber', 'taxi', 'bus', 'train'],
                'shopping': ['amazon', 'store', 'mall', 'retail'],
                'utilities': ['electric', 'water', 'internet', 'phone']
            }
            keywords = category_keywords.get(category, [])
            if keywords:
                condition = " OR ".join([f"lower(`Description 1`) like '%{kw}%'" for kw in keywords])
                df = df.filter(f"({condition})")

        if args.get("date_from"):
            df = df.filter(f"`Transaction Date` >= '{args['date_from']}'")
        if args.get("date_to"):
            df = df.filter(f"`Transaction Date` <= '{args['date_to']}'")
        if args.get("account_type"):
            df = df.filter(f"lower(`Account Type`) = lower('{args['account_type']}')")

        # Calculate spending metrics
        spending_df = df.filter("`CAD$` < 0") \
            .withColumn("amount", -col("CAD$")) \
            .agg(
                spark_sum("amount").alias("total_spent"),
                count("amount").alias("transaction_count"),
                avg("amount").alias("avg_transaction"),
                max("amount").alias("largest_transaction")
            )

        results = spending_df.collect()
        if not results:
            # No data found
            results = {
                'total_spent': 0.0,
                'transaction_count': 0,
                'avg_transaction': 0.0,
                'largest_transaction': 0.0
            }
        else:
            results = results[0]
            # Handle potential null values
            results = {
                'total_spent': results['total_spent'] if results['total_spent'] is not None else 0.0,
                'transaction_count': results['transaction_count'] if results['transaction_count'] is not None else 0,
                'avg_transaction': results['avg_transaction'] if results['avg_transaction'] is not None else 0.0,
                'largest_transaction': results['largest_transaction'] if results['largest_transaction'] is not None else 0.0
            }

        analysis = f"""Spending Analysis Results:
- Total Spent: ${results['total_spent']:.2f}
- Number of Transactions: {results['transaction_count']}
- Average Transaction: ${results['avg_transaction']:.2f}
- Largest Transaction: ${results['largest_transaction']:.2f}"""

        if args.get("category"):
            analysis += f"\nFiltered by category: {args['category']}"

        return [TextContent(type="text", text=analysis)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error analyzing spending: {str(e)}")]

async def handle_categorize_transactions(args: dict):
    """Handle categorize_transactions tool"""
    from mcp.types import TextContent
    from pyspark.sql.functions import col, sum as spark_sum, count, avg, udf, when
    try:
        df = load_transaction_data()

        # Apply filters
        if args.get("date_from"):
            df = df.filter(f"`Transaction Date` >= '{args['date_from']}'")
        if args.get("date_to"):
            df = df.filter(f"`Transaction Date` <= '{args['date_to']}'")
        if args.get("min_amount"):
            df = df.filter(f"abs(`CAD$`) >= {args['min_amount']}")

        # Simple categorization using SQL CASE statements instead of UDF
        categorized_df = df.withColumn("category", 
            when(col("`Description 1`").rlike("(?i)(restaurant|cafe|coffee|food|grocery)"), "Food & Dining")
            .when(col("`Description 1`").rlike("(?i)(gas|uber|taxi|bus|train|parking)"), "Transportation")
            .when(col("`Description 1`").rlike("(?i)(movie|game|music|netflix|spotify)"), "Entertainment")
            .when(col("`Description 1`").rlike("(?i)(amazon|walmart|store|mall)"), "Shopping")
            .when(col("`Description 1`").rlike("(?i)(electric|water|internet|phone|rent)"), "Utilities & Housing")
            .otherwise("Other")
        ) \
            .filter("`CAD$` < 0") \
            .withColumn("amount", -col("CAD$")) \
            .groupBy("category") \
            .agg(
                spark_sum("amount").alias("total_spent"),
                count("amount").alias("transaction_count"),
                avg("amount").alias("avg_amount")
            ) \
            .orderBy(col("total_spent").desc())

        results = categorized_df.collect()

        analysis = "Transaction Categories Summary:\n"
        for row in results:
            analysis += f"- {row['category']}: ${row['total_spent']:.2f} ({row['transaction_count']} transactions, avg: ${row['avg_amount']:.2f})\n"

        return [TextContent(type="text", text=analysis)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error categorizing transactions: {str(e)}")]

async def handle_detect_anomalies(args: dict):
    """Handle detect_anomalies tool"""
    from mcp.types import TextContent
    from pyspark.sql.functions import col
    try:
        df = load_transaction_data()
        threshold = args.get("threshold", 500)

        # Apply date filters
        if args.get("date_from"):
            df = df.filter(f"`Transaction Date` >= '{args['date_from']}'")
        if args.get("date_to"):
            df = df.filter(f"`Transaction Date` <= '{args['date_to']}'")

        # Find transactions above threshold
        anomalies_df = df.filter(f"abs(`CAD$`) >= {threshold}") \
            .select("Transaction Date", "Description 1", "CAD$", "Account Type") \
            .orderBy(col("CAD$").desc())

        results = anomalies_df.collect()

        if not results:
            return [TextContent(type="text", text=f"No transactions found above ${threshold} threshold.")]

        analysis = f"Unusual Transactions (≥${threshold}):\n"
        for row in results:
            amount = float(row['CAD$'])
            analysis += f"- {row['Transaction Date']}: {row['Description 1']} - ${amount:.2f}\n"

        return [TextContent(type="text", text=analysis)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error detecting anomalies: {str(e)}")]

async def handle_compare_periods(args: dict):
    """Handle compare_periods tool"""
    from mcp.types import TextContent
    from pyspark.sql.functions import col, sum as spark_sum
    try:
        df = load_transaction_data()

        # Period 1
        period1_df = df.filter(f"`Transaction Date` >= '{args['period1_start']}'") \
            .filter(f"`Transaction Date` <= '{args['period1_end']}'") \
            .filter("`CAD$` < 0") \
            .withColumn("amount", -col("CAD$")) \
            .agg(spark_sum("amount").alias("period1_total"))

        # Period 2
        period2_df = df.filter(f"`Transaction Date` >= '{args['period2_start']}'") \
            .filter(f"`Transaction Date` <= '{args['period2_end']}'") \
            .filter("`CAD$` < 0") \
            .withColumn("amount", -col("CAD$")) \
            .agg(spark_sum("amount").alias("period2_total"))

        p1_results = period1_df.collect()
        p2_results = period2_df.collect()
        
        p1_total = p1_results[0]['period1_total'] if p1_results and p1_results[0]['period1_total'] is not None else 0.0
        p2_total = p2_results[0]['period2_total'] if p2_results and p2_results[0]['period2_total'] is not None else 0.0
        difference = p2_total - p1_total
        percent_change = (difference / p1_total) * 100 if p1_total > 0 else 0

        analysis = f"""Period Comparison Results:

Period 1 ({args['period1_start']} to {args['period1_end']}): ${p1_total:.2f}
Period 2 ({args['period2_start']} to {args['period2_end']}): ${p2_total:.2f}

Difference: ${difference:.2f} ({percent_change:+.1f}%)"""

        if difference > 0:
            analysis += "\n⚠️ Spending increased in the second period."
        else:
            analysis += "\n✅ Spending decreased in the second period."

        return [TextContent(type="text", text=analysis)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error comparing periods: {str(e)}")]

@server.list_resources()
async def list_resources():
    """List available resources"""
    from mcp.types import Resource
    return [
        Resource(
            uri="transaction://schema",
            name="Transaction Data Schema",
            description="Schema information for transaction data",
            mimeType="text/plain"
        ),
        Resource(
            uri="transaction://stats",
            name="Transaction Dataset Statistics",
            description="Basic statistics about the transaction dataset",
            mimeType="text/plain"
        )
    ]

@server.read_resource()
async def read_resource(uri: str):
    """Read resource content"""
    from pyspark.sql.functions import col, sum as spark_sum, count, min, max
    if uri == "transaction://schema":
        try:
            df = load_transaction_data()
            schema_info = "Transaction Data Schema:\n"
            for field in df.schema.fields:
                schema_info += f"- {field.name}: {field.dataType}\n"
            return schema_info
        except Exception as e:
            return f"Error getting schema: {str(e)}"

    elif uri == "transaction://stats":
        try:
            df = load_transaction_data()

            stats_df = df.agg(
                count("*").alias("total_transactions"),
                count("distinct(`Account Number`)").alias("unique_accounts"),
                min("`Transaction Date`").alias("earliest_date"),
                max("`Transaction Date`").alias("latest_date")
            )

            stats = stats_df.collect()[0]

            spending_results = spending_df.collect()
            total_spent = spending_results[0]['total_spent'] if spending_results and spending_results[0]['total_spent'] is not None else 0.0

            income_results = income_df.collect()
            total_income = income_results[0]['total_income'] if income_results and income_results[0]['total_income'] is not None else 0.0

            stats_text = f"""Transaction Dataset Statistics:
- Total Transactions: {stats['total_transactions']}
- Unique Accounts: {stats['unique_accounts']}
- Date Range: {stats['earliest_date']} to {stats['latest_date']}
- Total Spent: ${total_spent:.2f}
- Total Income: ${total_income:.2f}
- Net Flow: ${total_income - total_spent:.2f}"""

            return stats_text

        except Exception as e:
            return f"Error getting stats: {str(e)}"

    else:
        raise ValueError(f"Unknown resource: {uri}")

async def main():
    from mcp.server.stdio import stdio_server
    print("Starting MCP server...", file=os.sys.stderr)

    async with stdio_server() as (read_stream, write_stream):
        try:
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
        except Exception as e:
            print(f"Server runtime error: {e}", file=os.sys.stderr)
            raise

if __name__ == "__main__":
    asyncio.run(main())