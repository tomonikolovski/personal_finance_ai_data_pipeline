from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import textwrap
import subprocess
from llama_cpp import Llama
import os

# optional OpenAI support
try:
    import openai
except ImportError:
    openai = None

SCRIPT_TEMPLATE = '''
import argparse
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import col
import sys
import socket 

def setup_logger():
    # Configure the logger
    logger = logging.getLogger("S3SparkLogger")
    logger.setLevel(logging.DEBUG)
    
    # Create a console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    
    # Create a formatter and set it for the handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    
    # Add the handler to the logger
    logger.addHandler(ch)
    
    return logger

def transactions_analyzer_default(data_frame, spark):
    try:
        filtered_df = data_frame.filter(col("CAD$") > 0)
        filtered_df.show()
        logger.info("Successfully filtered DataFrame.")
    except Exception as e:
        logger.error("Error filtering DataFrame: {{}}".format(e))
    finally:
        spark.stop()
        logger.info("Spark session stopped.")

{transactions_analyzer}

def main():
    try:
        minio_ip = socket.gethostbyname("minio")
        spark = SparkSession.builder \
            .appName("ListFilesOnMinIO") \
            .config("spark.master", "spark://host.docker.internal:7077") \
            .config("spark.hadoop.fs.s3a.access.key", args.access) \
            .config("spark.hadoop.fs.s3a.secret.key", args.secret) \
            .config("spark.hadoop.fs.s3a.endpoint", 'http://{{}}:9000'.format(minio_ip)) \
            .getOrCreate()
        logger.info("Spark session created successfully.")
        spark.sparkContext.setLogLevel("ERROR")
    except Exception as e:
        logger.error("Error creating Spark session: {{}}".format(e))
        sys.exit(1)

    try:
        df = spark.read.json(args.s3_path)
        transactions_analyzer(df, spark)
    except Exception as e:
        logger.error(e)
        spark.stop()
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process S3 connection details and S3 path.')
    parser.add_argument('--access', required=True, help='S3 Access Key')
    parser.add_argument('--secret', required=True, help='S3 Secret Key')
    parser.add_argument('--s3_path', required=True, help='S3 Path for JSON files')

    args = parser.parse_args()

    logger = setup_logger()

    main()

'''
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <-- or be specific with ["http://localhost:8080"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_PATH = os.getenv("MODEL_PATH", "llm/codellama-7b-instruct.Q4_K_M.gguf")
SPARK_MASTER = os.getenv("SPARK_MASTER", "spark://spark-master:7077")

# choose whether to call OpenAI or local Llama
USE_OPENAI = os.getenv("USE_OPENAI", "false").lower() in ("1","true","yes")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")

# initialize local LLM only if needed
llm = None
if not USE_OPENAI:
    llm = Llama(
        model_path=MODEL_PATH,  
        n_ctx=4096,   # Context size, adjust as needed
        n_threads=8,  # Depends on CPU
        temperature=0.2,  # Lower temp for more deterministic code output
    )

class Prompt(BaseModel):
    description: str

@app.post("/generate-and-run")
async def generate_and_run(prompt: Prompt):
    prompt_text = f"""
    You are a helpful assistant that generates a function definition only.

    Generate a complete transactions_analyzer(data_frame, spark) method using PySpark, based on the following description:

    \"\"\"
    {prompt.description}
    \"\"\"

    The data_frame has columns: "Account Number", "Account Type", "CAD$", "Description 1", "Transaction Date".
    "CAD$" is amount, "Description 1" is the company name.

    Guidelines:
    - Only output the full Python function: "def transactions_analyzer(data_frame, spark):"
    - Do not generate anything else aside from the function code
    - Generate a simple code
    - Use pyspark to work with the data_frame
    - Don't return anything from the function
    - Use 'logger' for logging
    - Display the filtered data_frame with show() method
    - Always stop Spark with spark.stop() in finally block.
    """

    # Generate code from either OpenAI or the local LLM
    if USE_OPENAI:
        if openai is None:
            raise RuntimeError("OpenAI package not installed but USE_OPENAI is true")
        # New OpenAI python client (>=1.0.0) uses an OpenAI class.
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt_text}],
            max_tokens=2048,
            temperature=0.2,
        )
        # the structure remains similar for extracting the message text
        transactions_analyzer = textwrap.dedent(
            response.choices[0].message.content.strip().replace("\"\"\"", "")
        )
    else:
        output = llm(
            prompt_text,
            max_tokens=2048,   # Allow bigger responses
            stop=["Task Description:","Full PySpark Script:"],  # Make sure it stops after code
        )
        transactions_analyzer = textwrap.dedent(
            output["choices"][0]["text"].strip().replace("\"\"\"", "")
        )
    print(transactions_analyzer)

    full_script = SCRIPT_TEMPLATE.format(
        transactions_analyzer=transactions_analyzer
    )

    # Save to script
    with open("/tmp/generated_job.py", "w") as f:
        f.write(full_script)

    # Run Spark job
    cmd = [
        "spark-submit",
        "--master", SPARK_MASTER,
        "/tmp/generated_job.py",
        "--access", "minio",
        "--secret", "minio123",
        "--s3_path", "s3a://bucket1/topic1/partition=0/*.json"
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    return {
        "generated_code": transactions_analyzer,
        "output": result.stdout,
        "error": result.stderr
    }