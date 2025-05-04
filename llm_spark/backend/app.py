from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
from llama_cpp import Llama
import os

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

The data_frame has columns: Account Number, Account Type, CAD$, Description 1, Transaction Date.
CAD$ is amount, Description 1 is the company name.

Guidelines:
- Only output the full Python function: def transactions_analyzer(data_frame, spark): ...
- Use 'logger' for logging.
- Always stop Spark with spark.stop() in finally block.
"""
    # Generate code from LLM
    output = llm(
        prompt_text,
        max_tokens=2048,   # Allow bigger responses
        stop=["Task Description:","Full PySpark Script:"],  # Make sure it stops after code
    )
    code = output["choices"][0]["text"].strip()

    # Save to script
    with open("/tmp/generated_job.py", "w") as f:
        f.write(code)

    # Run Spark job
    cmd = [
        "spark-submit",
        "--master", SPARK_MASTER,
        "/tmp/generated_job.py"
    ]
    #result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    return {
        "generated_code": code,
    #    "output": result.stdout,
    #    "error": result.stderr
    }

