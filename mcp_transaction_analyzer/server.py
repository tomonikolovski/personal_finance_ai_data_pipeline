#!/usr/bin/env python3
"""
MCP Server for Transaction Analysis Domain

Provides AI-powered financial transaction analysis over MinIO + Spark.
Sign convention: negative CAD$ = withdrawal/spending, positive CAD$ = incoming money/income.
"""

import asyncio
import os
from typing import Any, Optional

from mcp.server.lowlevel import Server

server = Server("transaction-analyzer")

spark: Optional["SparkSession"] = None
s3_client = None


# ---------------------------------------------------------------------------
# Spark / S3 initialisation (unchanged from original)
# ---------------------------------------------------------------------------

def init_spark():
    global spark
    if spark is None:
        try:
            import sys
            from pyspark.sql import SparkSession

            if 'SPARK_HOME' not in os.environ:
                for candidate in [
                    '/opt/spark/spark-3.5.1-bin-hadoop3',
                    '/usr/local/spark',
                    os.path.join(os.path.dirname(__file__), '..', 'spark-client', 'spark-3.5.1-bin-hadoop3'),
                ]:
                    if os.path.exists(candidate):
                        os.environ['SPARK_HOME'] = candidate
                        break

            if 'JAVA_HOME' not in os.environ:
                import subprocess
                try:
                    out = subprocess.check_output(['java', '-XshowSettings:properties', '-version'],
                                                  stderr=subprocess.STDOUT, text=True)
                    for line in out.split('\n'):
                        if 'java.home' in line:
                            os.environ['JAVA_HOME'] = line.split('=')[1].strip()
                            break
                except Exception as e:
                    print(f"Could not determine JAVA_HOME: {e}", file=os.sys.stderr)

            os.environ.setdefault('PYSPARK_PYTHON', sys.executable)
            os.environ.setdefault('PYSPARK_DRIVER_PYTHON', sys.executable)
            os.environ.setdefault('JAVA_OPTS',
                '--add-opens java.base/javax.security.auth=ALL-UNNAMED '
                '--add-opens java.base/java.lang=ALL-UNNAMED '
                '--add-opens java.base/java.util=ALL-UNNAMED')

            spark = (
                SparkSession.builder
                .appName("TransactionAnalyzer")
                .config("spark.hadoop.fs.s3a.access.key", os.getenv("MINIO_ACCESS_KEY", "minio"))
                .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_SECRET_KEY", "minio123"))
                .config("spark.hadoop.fs.s3a.endpoint", os.getenv("MINIO_ENDPOINT", "http://minio:9000"))
                .config("spark.hadoop.fs.s3a.path.style.access", "true")
                .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
                .config("spark.hadoop.security.authentication", "simple")
                .config("spark.hadoop.security.authorization", "false")
                .config("spark.hadoop.fs.s3a.aws.credentials.provider",
                        "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider")
                .config("spark.ui.enabled", "false")
                .config("spark.master", os.getenv("SPARK_MASTER_URL", "local[*]"))
                .config("spark.driver.memory", "512m")
                .config("spark.executor.memory", "512m")
                .config("spark.sql.adaptive.enabled", "false")
                .config("spark.driver.extraJavaOptions",
                        "--add-opens java.base/javax.security.auth=ALL-UNNAMED")
                .config("spark.executor.extraJavaOptions",
                        "--add-opens java.base/javax.security.auth=ALL-UNNAMED")
                .getOrCreate()
            )
            spark.sql("SELECT 1").collect()
            print("Spark session initialised successfully", file=os.sys.stderr)
        except Exception as e:
            print(f"Warning: Spark initialisation failed: {e}", file=os.sys.stderr)
            spark = None
    return spark


def init_s3():
    global s3_client
    if s3_client is None:
        import boto3
        s3_client = boto3.client(
            's3',
            endpoint_url=os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
            aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minio"),
            aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minio123"),
            region_name='us-east-1',
        )
    return s3_client


def load_transaction_data(bucket: str = "bucket1", prefix: str = "topic1/partition=0/",
                          date_from: str = None, date_to: str = None) -> Any:
    """
    Load transaction data from MinIO into a Spark DataFrame.

    Raw JSON from Kafka has two quirks that are fixed here at load time:
      - `CAD$` arrives as a string (e.g. "-4", "-65.54") → cast to double
      - `Transaction Date` is M/D/YYYY (e.g. "4/15/2024") → parsed to a
        proper date column called `tx_date` so filtering and grouping work
        correctly.  The original string column is left intact.
    """
    spark_session = init_spark()
    if spark_session is None:
        raise Exception("Spark is not available. Check server logs for details.")

    s3_path = f"s3a://{bucket}/{prefix}*.json"
    try:
        from pyspark.sql.functions import col, to_date, to_timestamp

        df = spark_session.read.json(s3_path)

        # Cast amount to numeric — it arrives as a string from Kafka's CSV serialiser
        df = df.withColumn("amount", col("`CAD$`").cast("double"))

        # Parse the M/D/YYYY date string into a proper DateType column
        df = df.withColumn("tx_date", to_date(col("`Transaction Date`"), "M/d/yyyy"))

        # Apply optional date-range filters against the parsed date column
        if date_from:
            df = df.filter(col("tx_date") >= date_from)
        if date_to:
            df = df.filter(col("tx_date") <= date_to)

        return df
    except Exception as e:
        raise Exception(f"Failed to load data from {s3_path}: {e}")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _apply_date_filters(df, args: dict):
    """Filter on the parsed `tx_date` DateType column (accepts YYYY-MM-DD strings)."""
    from pyspark.sql.functions import col
    if args.get("date_from"):
        df = df.filter(col("tx_date") >= args["date_from"])
    if args.get("date_to"):
        df = df.filter(col("tx_date") <= args["date_to"])
    return df


# CAD$ < 0  →  withdrawal / spending
# CAD$ > 0  →  income / incoming money
# Applied via df.withColumn("category", expr(CATEGORY_EXPR))
# References the `Description 1` column using backtick quoting inside the SQL expression.
CATEGORY_EXPR = """
    CASE
        WHEN lower(`Description 1`) rlike '(restaurant|cafe|coffee|food|grocery|grocer|bakery|pizza|sushi|burger)' THEN 'Food & Dining'
        WHEN lower(`Description 1`) rlike '(gas station|petro|esso|shell|uber|lyft|taxi|bus|train|transit|parking|via rail)' THEN 'Transportation'
        WHEN lower(`Description 1`) rlike '(netflix|spotify|apple music|disney|prime video|cinema|movie|theatre|game|steam|xbox|playstation)' THEN 'Entertainment'
        WHEN lower(`Description 1`) rlike '(amazon|walmart|costco|ikea|best buy|shopify|shop|store|mall|zara|h&m|ebay)' THEN 'Shopping'
        WHEN lower(`Description 1`) rlike '(hydro|enbridge|bell|rogers|telus|fido|koodo|virgin|internet|phone|rent|lease|condo|mortgage)' THEN 'Utilities & Housing'
        WHEN lower(`Description 1`) rlike '(pharmacy|shoppers|rexall|medical|hospital|clinic|dental|optom|drug)' THEN 'Health & Pharmacy'
        WHEN lower(`Description 1`) rlike '(transfer|e-transfer|etransfer|interac|wire|deposit|refund|rebate|cashback|interest|dividend|payroll|direct deposit)' THEN 'Transfers & Income'
        WHEN lower(`Description 1`) rlike '(insurance|assurance|aviva|intact|sunlife|manulife|desjardins)' THEN 'Insurance'
        WHEN lower(`Description 1`) rlike '(atm|cash|withdrawal)' THEN 'Cash & ATM'
        ELSE 'Other'
    END
"""


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

@server.list_tools()
async def list_tools():
    from mcp.types import Tool
    return [
        Tool(
            name="monthly_spending_summary",
            description=(
                "Show total spending and income broken down by month. "
                "Negative CAD$ values are withdrawals/spending; positive are incoming money. "
                "Use this to answer questions like 'how much did I spend each month?' or "
                "'show me my monthly cash flow'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "date_to":   {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "account_type": {"type": "string", "description": "Filter by account type (e.g. chequing, savings)"},
                }
            }
        ),
        Tool(
            name="top_transactions",
            description=(
                "Return the largest transactions by absolute amount. "
                "Can filter to only spending (withdrawals) or only income (deposits). "
                "Use this to answer 'what is the largest transaction?' or 'show me my biggest expenses'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit":      {"type": "integer", "description": "Number of transactions to return (default 10)"},
                    "direction":  {"type": "string",  "description": "'spending' for withdrawals, 'income' for deposits, omit for both"},
                    "date_from":  {"type": "string",  "description": "Start date (YYYY-MM-DD)"},
                    "date_to":    {"type": "string",  "description": "End date (YYYY-MM-DD)"},
                }
            }
        ),
        Tool(
            name="merchant_summary",
            description=(
                "Summarise spending or income grouped by merchant / description. "
                "Use this to answer 'where am I spending the most?' or 'which merchants do I use most often?'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "direction":  {"type": "string",  "description": "'spending' (default) or 'income'"},
                    "limit":      {"type": "integer", "description": "Number of merchants to return (default 15)"},
                    "date_from":  {"type": "string",  "description": "Start date (YYYY-MM-DD)"},
                    "date_to":    {"type": "string",  "description": "End date (YYYY-MM-DD)"},
                    "min_amount": {"type": "number",  "description": "Minimum total amount to include a merchant"},
                }
            }
        ),
        Tool(
            name="categorize_transactions",
            description=(
                "Group transactions into categories (Food, Transport, Entertainment, etc.) "
                "with totals and transaction counts. Shows spending and income separately. "
                "Use this for 'categorize my spending' or 'what category costs the most?'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "direction":  {"type": "string",  "description": "'spending' (default), 'income', or 'both'"},
                    "date_from":  {"type": "string",  "description": "Start date (YYYY-MM-DD)"},
                    "date_to":    {"type": "string",  "description": "End date (YYYY-MM-DD)"},
                    "min_amount": {"type": "number",  "description": "Minimum transaction amount (absolute value) to include"},
                }
            }
        ),
        Tool(
            name="compare_periods",
            description=(
                "Compare total spending and income between two date ranges. "
                "Returns the difference and percentage change for each direction."
            ),
            inputSchema={
                "type": "object",
                "required": ["period1_start", "period1_end", "period2_start", "period2_end"],
                "properties": {
                    "period1_start": {"type": "string", "description": "Period 1 start (YYYY-MM-DD)"},
                    "period1_end":   {"type": "string", "description": "Period 1 end (YYYY-MM-DD)"},
                    "period2_start": {"type": "string", "description": "Period 2 start (YYYY-MM-DD)"},
                    "period2_end":   {"type": "string", "description": "Period 2 end (YYYY-MM-DD)"},
                }
            }
        ),
        Tool(
            name="detect_anomalies",
            description=(
                "Find unusually large transactions above a threshold. "
                "Clearly labels each result as spending (withdrawal) or income (deposit). "
                "Use to spot unexpected large charges or payments."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "threshold": {"type": "number", "description": "Absolute amount threshold (default 500)"},
                    "direction": {"type": "string", "description": "'spending', 'income', or omit for both"},
                    "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "date_to":   {"type": "string", "description": "End date (YYYY-MM-DD)"},
                }
            }
        ),
    ]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    from mcp.types import TextContent
    handlers = {
        "monthly_spending_summary": handle_monthly_spending_summary,
        "top_transactions":         handle_top_transactions,
        "merchant_summary":         handle_merchant_summary,
        "categorize_transactions":  handle_categorize_transactions,
        "compare_periods":          handle_compare_periods,
        "detect_anomalies":         handle_detect_anomalies,
    }
    handler = handlers.get(name)
    if handler is None:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    try:
        return await handler(arguments)
    except Exception as e:
        return [TextContent(type="text", text=f"Error in tool '{name}': {e}")]


async def handle_monthly_spending_summary(args: dict):
    """Break down spending and income by calendar month."""
    from mcp.types import TextContent
    from pyspark.sql.functions import col, sum as spark_sum, count, date_format

    df = load_transaction_data()
    df = _apply_date_filters(df, args)
    if args.get("account_type"):
        df = df.filter(f"lower(`Account Type`) = lower('{args['account_type']}')")

    # tx_date is a proper DateType — format it as YYYY-MM for grouping
    df = df.withColumn("month", date_format(col("tx_date"), "yyyy-MM"))

    spending_df = (
        df.filter(col("amount") < 0)
          .groupBy("month")
          .agg(spark_sum(-col("amount")).alias("total_spent"),
               count("*").alias("spending_txns"))
    )

    income_df = (
        df.filter(col("amount") > 0)
          .groupBy("month")
          .agg(spark_sum("amount").alias("total_income"),
               count("*").alias("income_txns"))
    )

    joined = spending_df.join(income_df, on="month", how="full_outer") \
                        .orderBy("month")

    rows = joined.collect()
    if not rows:
        return [TextContent(type="text", text="No transactions found for the selected period.")]

    lines = ["Monthly Summary (spending = withdrawals, income = deposits):\n",
             f"{'Month':<10}  {'Spent':>10}  {'Income':>10}  {'Net':>10}  Txns"]
    lines.append("-" * 58)
    for r in rows:
        spent  = float(r['total_spent']  or 0)
        income = float(r['total_income'] or 0)
        net    = income - spent
        s_txns = int(r['spending_txns'] or 0)
        i_txns = int(r['income_txns']   or 0)
        lines.append(
            f"{r['month']:<10}  ${spent:>9.2f}  ${income:>9.2f}  ${net:>+9.2f}  "
            f"{s_txns} out / {i_txns} in"
        )

    return [TextContent(type="text", text="\n".join(lines))]


async def handle_top_transactions(args: dict):
    """Return the N largest transactions by absolute value."""
    from mcp.types import TextContent
    from pyspark.sql.functions import col, abs as spark_abs

    df = load_transaction_data()
    df = _apply_date_filters(df, args)

    direction = args.get("direction", "both").lower()
    if direction == "spending":
        df = df.filter(col("amount") < 0)
    elif direction == "income":
        df = df.filter(col("amount") > 0)

    limit = int(args.get("limit", 10))

    top_df = (
        df.withColumn("abs_amount", spark_abs(col("amount")))
          .select("tx_date", "`Description 1`", "amount", "`Account Type`", "abs_amount")
          .orderBy(col("abs_amount").desc())
          .limit(limit)
    )

    rows = top_df.collect()
    if not rows:
        return [TextContent(type="text", text="No transactions found.")]

    title = {"spending": "Largest Spending Transactions",
             "income":   "Largest Incoming Transactions"}.get(direction, "Largest Transactions")

    lines = [f"{title} (top {limit}):\n",
             f"{'Date':<12}  {'Amount':>10}  {'Type':<6}  Description"]
    lines.append("-" * 70)
    for r in rows:
        amount = float(r['amount'])
        kind   = "OUT" if amount < 0 else "IN "
        lines.append(
            f"{str(r['tx_date']):<12}  ${abs(amount):>9.2f}  {kind}  {r['Description 1']}"
        )

    return [TextContent(type="text", text="\n".join(lines))]


async def handle_merchant_summary(args: dict):
    """Group by merchant/description and sum amounts."""
    from mcp.types import TextContent
    from pyspark.sql.functions import col, sum as spark_sum, count, avg

    df = load_transaction_data()
    df = _apply_date_filters(df, args)

    direction = args.get("direction", "spending").lower()
    limit     = int(args.get("limit", 15))

    if direction == "income":
        df = df.filter(col("amount") > 0)
        label = "Income"
    else:
        df = df.filter(col("amount") < 0).withColumn("amount", -col("amount"))
        label = "Spending"

    if args.get("min_amount"):
        df = df.filter(col("amount") >= args["min_amount"])

    summary_df = (
        df.groupBy("`Description 1`")
          .agg(
              spark_sum("amount").alias("total"),
              count("*").alias("txn_count"),
              avg("amount").alias("avg_amount"),
          )
          .orderBy(col("total").desc())
          .limit(limit)
    )

    rows = summary_df.collect()
    if not rows:
        return [TextContent(type="text", text="No transactions found.")]

    lines = [f"Merchant {label} Summary (top {limit}):\n",
             f"{'Total':>10}  {'Count':>5}  {'Avg':>8}  Merchant"]
    lines.append("-" * 70)
    for r in rows:
        lines.append(
            f"${float(r['total']):>9.2f}  {int(r['txn_count']):>5}  "
            f"${float(r['avg_amount']):>7.2f}  {r['Description 1']}"
        )

    return [TextContent(type="text", text="\n".join(lines))]


async def handle_categorize_transactions(args: dict):
    """Categorize transactions and summarise by category."""
    from mcp.types import TextContent
    from pyspark.sql.functions import col, sum as spark_sum, count, avg, expr, abs as spark_abs

    df = load_transaction_data()
    df = _apply_date_filters(df, args)
    if args.get("min_amount"):
        df = df.filter(spark_abs(col("amount")) >= args["min_amount"])

    direction = args.get("direction", "spending").lower()
    df = df.withColumn("category", expr(CATEGORY_EXPR))

    output_sections = []

    if direction in ("spending", "both"):
        spend_df = (
            df.filter(col("amount") < 0)
              .groupBy("category")
              .agg(spark_sum(-col("amount")).alias("total"),
                   count("*").alias("txn_count"),
                   avg(-col("amount")).alias("avg_amount"))
              .orderBy(col("total").desc())
        )
        rows = spend_df.collect()
        grand = sum(float(r['total']) for r in rows)
        lines = [f"Spending by Category (total: ${grand:.2f}):\n",
                 f"{'Total':>10}  {'%':>5}  {'Count':>5}  {'Avg':>8}  Category"]
        lines.append("-" * 60)
        for r in rows:
            t = float(r['total'])
            pct = (t / grand * 100) if grand else 0
            lines.append(
                f"${t:>9.2f}  {pct:>4.1f}%  {int(r['txn_count']):>5}  "
                f"${float(r['avg_amount']):>7.2f}  {r['category']}"
            )
        output_sections.append("\n".join(lines))

    if direction in ("income", "both"):
        income_df = (
            df.filter(col("amount") > 0)
              .groupBy("category")
              .agg(spark_sum("amount").alias("total"),
                   count("*").alias("txn_count"),
                   avg("amount").alias("avg_amount"))
              .orderBy(col("total").desc())
        )
        rows = income_df.collect()
        grand = sum(float(r['total']) for r in rows)
        lines = [f"\nIncome by Category (total: ${grand:.2f}):\n",
                 f"{'Total':>10}  {'%':>5}  {'Count':>5}  {'Avg':>8}  Category"]
        lines.append("-" * 60)
        for r in rows:
            t = float(r['total'])
            pct = (t / grand * 100) if grand else 0
            lines.append(
                f"${t:>9.2f}  {pct:>4.1f}%  {int(r['txn_count']):>5}  "
                f"${float(r['avg_amount']):>7.2f}  {r['category']}"
            )
        output_sections.append("\n".join(lines))

    return [TextContent(type="text", text="\n\n".join(output_sections))]


async def handle_compare_periods(args: dict):
    """Compare spending and income across two date ranges."""
    from mcp.types import TextContent
    from pyspark.sql.functions import col, sum as spark_sum

    df = load_transaction_data()

    def period_stats(start, end):
        p = df.filter(col("tx_date") >= start).filter(col("tx_date") <= end)
        spent  = p.filter(col("amount") < 0).agg(spark_sum(-col("amount")).alias("v")).collect()[0]['v'] or 0.0
        income = p.filter(col("amount") > 0).agg(spark_sum("amount").alias("v")).collect()[0]['v'] or 0.0
        return float(spent), float(income)

    s1, i1 = period_stats(args['period1_start'], args['period1_end'])
    s2, i2 = period_stats(args['period2_start'], args['period2_end'])

    def pct(new, old):
        return ((new - old) / old * 100) if old else 0

    lines = [
        "Period Comparison:\n",
        f"                         Period 1 ({args['period1_start']} → {args['period1_end']})"
        f"    Period 2 ({args['period2_start']} → {args['period2_end']})",
        "-" * 80,
        f"{'Spending (withdrawals)':<25} ${s1:>10.2f}                    ${s2:>10.2f}   ({pct(s2, s1):+.1f}%)",
        f"{'Income (deposits)':<25} ${i1:>10.2f}                    ${i2:>10.2f}   ({pct(i2, i1):+.1f}%)",
        f"{'Net flow':<25} ${i1-s1:>+10.2f}                    ${i2-s2:>+10.2f}",
        "",
    ]

    lines.append("⚠️  Spending increased in the second period." if s2 > s1
                 else "✅  Spending decreased (or stayed the same) in the second period.")
    if i2 > i1:
        lines.append("📈  Income increased in the second period.")
    elif i2 < i1:
        lines.append("📉  Income decreased in the second period.")

    return [TextContent(type="text", text="\n".join(lines))]


async def handle_detect_anomalies(args: dict):
    """Flag unusually large transactions, labelling each as spending or income."""
    from mcp.types import TextContent
    from pyspark.sql.functions import col, abs as spark_abs

    df = load_transaction_data()
    df = _apply_date_filters(df, args)

    threshold = float(args.get("threshold", 500))
    direction = args.get("direction", "both").lower()

    if direction == "spending":
        df = df.filter(col("amount") < 0)
    elif direction == "income":
        df = df.filter(col("amount") > 0)

    anomalies_df = (
        df.withColumn("abs_amount", spark_abs(col("amount")))
          .filter(col("abs_amount") >= threshold)
          .select("tx_date", "`Description 1`", "amount", "`Account Type`", "abs_amount")
          .orderBy(col("abs_amount").desc())
    )

    rows = anomalies_df.collect()
    if not rows:
        return [TextContent(type="text", text=f"No transactions found with absolute amount ≥ ${threshold:.2f}.")]

    lines = [f"Large Transactions (≥ ${threshold:.2f}):\n",
             f"{'Date':<12}  {'Amount':>10}  {'Type':<7}  Description"]
    lines.append("-" * 70)
    for r in rows:
        amount = float(r['amount'])
        kind   = "SPEND" if amount < 0 else "INCOME"
        lines.append(
            f"{str(r['tx_date']):<12}  ${abs(amount):>9.2f}  {kind:<7}  {r['Description 1']}"
        )

    return [TextContent(type="text", text="\n".join(lines))]


# ---------------------------------------------------------------------------
# Resources  (fixed — spending_df / income_df were undefined in original)
# ---------------------------------------------------------------------------

@server.list_resources()
async def list_resources():
    from mcp.types import Resource
    return [
        Resource(
            uri="transaction://schema",
            name="Transaction Data Schema",
            description="Column names and data types in the transaction dataset",
            mimeType="text/plain",
        ),
        Resource(
            uri="transaction://stats",
            name="Transaction Dataset Statistics",
            description="Record count, date range, total spending, total income, and net flow",
            mimeType="text/plain",
        ),
        Resource(
            uri="transaction://categories",
            name="Category Keyword Reference",
            description="Lists the keywords used to classify transactions into categories",
            mimeType="text/plain",
        ),
    ]


@server.read_resource()
async def read_resource(uri: str):
    from pyspark.sql.functions import col, sum as spark_sum, count, min as spark_min, max as spark_max

    if uri == "transaction://schema":
        try:
            df = load_transaction_data()
            lines = [
                "Transaction Data Schema (as stored in MinIO JSON):\n",
                "  CAD$              : string in source → cast to double as `amount`",
                "  Transaction Date  : string M/D/YYYY  → parsed to DateType as `tx_date`",
                "  Description 1     : string  (merchant / payee name)",
                "  Description 2     : string  (usually empty)",
                "  Account Type      : string  (e.g. Visa, Chequing)",
                "  Account Number    : string",
                "  Cheque Number     : string  (usually empty)",
                "  USD$              : string  (usually empty)",
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"Error reading schema: {e}"

    elif uri == "transaction://stats":
        try:
            df = load_transaction_data()

            base = df.agg(
                count("*").alias("total_transactions"),
                spark_min("tx_date").alias("earliest_date"),
                spark_max("tx_date").alias("latest_date"),
            ).collect()[0]

            spent  = df.filter(col("amount") < 0) \
                       .agg(spark_sum(-col("amount")).alias("v")).collect()[0]['v'] or 0.0
            income = df.filter(col("amount") > 0) \
                       .agg(spark_sum("amount").alias("v")).collect()[0]['v'] or 0.0
            spent, income = float(spent), float(income)

            return (
                f"Transaction Dataset Statistics:\n"
                f"  Total records    : {base['total_transactions']}\n"
                f"  Date range       : {base['earliest_date']} → {base['latest_date']}\n"
                f"  Total spending   : ${spent:.2f}   (negative CAD$ = withdrawals)\n"
                f"  Total income     : ${income:.2f}   (positive CAD$ = deposits)\n"
                f"  Net cash flow    : ${income - spent:+.2f}\n"
            )
        except Exception as e:
            return f"Error reading stats: {e}"

    elif uri == "transaction://categories":
        return (
            "Category classification keywords (matched against Description 1, case-insensitive):\n\n"
            "  Food & Dining       : restaurant, cafe, coffee, food, grocery, bakery, pizza, sushi, burger\n"
            "  Transportation      : gas station, petro, esso, shell, uber, lyft, taxi, bus, train, transit, parking\n"
            "  Entertainment       : netflix, spotify, apple music, disney, prime video, cinema, movie, theatre, game, steam\n"
            "  Shopping            : amazon, walmart, costco, ikea, best buy, shopify, store, mall, zara, h&m, ebay\n"
            "  Utilities & Housing : hydro, enbridge, bell, rogers, telus, fido, internet, phone, rent, lease, condo, mortgage\n"
            "  Health & Pharmacy   : pharmacy, shoppers, rexall, medical, hospital, clinic, dental, optom, drug\n"
            "  Transfers & Income  : transfer, e-transfer, interac, wire, deposit, refund, rebate, payroll, direct deposit\n"
            "  Insurance           : insurance, aviva, intact, sunlife, manulife, desjardins\n"
            "  Cash & ATM          : atm, cash, withdrawal\n"
            "  Other               : everything else\n"
        )

    else:
        raise ValueError(f"Unknown resource: {uri}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    from mcp.server.stdio import stdio_server
    print("Starting MCP transaction-analyzer server...", file=os.sys.stderr)
    async with stdio_server() as (read_stream, write_stream):
        try:
            await server.run(read_stream, write_stream, server.create_initialization_options())
        except Exception as e:
            print(f"Server runtime error: {e}", file=os.sys.stderr)
            raise


if __name__ == "__main__":
    asyncio.run(main())