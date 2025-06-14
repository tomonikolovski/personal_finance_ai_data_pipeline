# Personal Finance AI Data Pipeline
Personal Finance AI Data Pipeline - Stream and store transactions. Analyze with Spark 3 and leverage a local LLM to write code based on human language input

## 🚀 Overview

This project is a personal finance AI data pipeline built to experiment with real-time data processing, storage, and AI-assisted analytics using modern open-source tools. It simulates a financial data workflow with both manual and AI-powered analysis capabilities.

🧩 Key Components

📥 Data Ingestion: Financial transactions (in CSV format) are streamed into Kafka.
🗂️ Data Storage: The streamed data is transformed into JSON and stored in MinIO (an S3-compatible object store).
📊 Data Analysis:
- Manually write PySpark scripts to analyze the stored data using Apache Spark 3.
- Or interact with a local LLM (Llama.cpp) through a FastAPI-based web interface. Users can enter natural language prompts (e.g., "Show me all transactions greater than 10 dollars").
  - The LLM will convert the prompt into a valid PySpark query.
  - The backend will execute the query against the Spark cluster.
  - Return and display the results in the Web UI.

## 🔧 Tech Stack and project components
This project leverages a modular set of open-source technologies to simulate a full AI-powered data analytics pipeline. Here's a breakdown of each component:

🌀 Kafka
Used for real-time streaming of financial transactions. Kafka handles the ingestion and buffering of data in motion.

🐘 Zookeeper
Required for managing Kafka in this setup. It maintains metadata and broker coordination. (Note: KRaft is a newer alternative that removes the Zookeeper dependency.)

🔗 Kafka Connect
Facilitates data transfer from Kafka topics to external storage. In this case, it streams Kafka messages into MinIO as JSON files.

🗄️ MinIO
An S3-compatible object storage system used to persist transaction data in a scalable, accessible format.

⚡ Apache Spark 3
Deployed as a Spark Master and one or more Workers, this cluster is responsible for distributed processing and analysis of the transaction data.

🐍 RHEL Container (PySpark CLI)
A pre-configured Red Hat Enterprise Linux container where users can manually run Python or PySpark scripts to interact with the stored data.

🌐 FastAPI Frontend
A lightweight web interface that allows users to input natural language prompts describing the analysis they want to perform.

🧠 LLM Backend (Llama.cpp inference)
A backend container running a local large language model via Llama.cpp. It:

- Interprets natural language prompts by using CodeLlama-7B-Instruct-GGUF model,
- Generates equivalent PySpark code,
- Executes the code on the Spark cluster, and
- Returns the results to the user.

## ⚙️ Project Setup & Usage Guide

Follow these steps to set up and run the project locally.

---
### 1. 📥 Clone the Repository

```bash
git clone https://github.com/tomonikolovski/personal_finance_data_pipeline_kafka_spark_minio.git
cd personal_finance_data_pipeline_kafka_spark_minio
```

---

### 2. 🤖 Download the LLM of choice CodeLlama-7B-Instruct.Q4_K_M
```bash
wget https://huggingface.co/TheBloke/CodeLlama-7B-Instruct-GGUF/resolve/main/codellama-7b-instruct.Q4_K_M.gguf -O codellama-7b-instruct.Q4_K_M.gguf
mkdir -p llm_spark/backend/llm
cp codellama-7b-instruct.Q4_K_M.gguf llm_spark/backend/llm/
```

---

### 3. ☕ Install Java (JDK 22)

Download and extract Java into the Spark client directory:

```bash
wget https://download.oracle.com/java/22/latest/jdk-22_linux-x64_bin.tar.gz
mkdir -p spark-client/jdk-22.0.1
tar -xzf jdk-22_linux-x64_bin.tar.gz -C spark-client/jdk-22.0.1 --strip-components=1
```

---
### 4. ⚡ Install Apache Spark 3.5.1

```bash
wget https://archive.apache.org/dist/spark/spark-3.5.1/spark-3.5.1-bin-hadoop3.tgz
mkdir -p spark-client/spark-3.5.1-bin-hadoop3
tar -xzf spark-3.5.1-bin-hadoop3.tgz -C spark-client/spark-3.5.1-bin-hadoop3 --strip-components=1
```

---
### 5. 📦 Install Required JARs for MinIO Integration

Download additional Jar files to be able to interract with MinIO buckets from PySpark
- Pre-compiled Maven already present under apache-maven-3.9.7
- pom.xml with all neccessary repos set up already 

```bash
cd apache-maven-3.9.7/bin
./mvn dependency:copy-dependencies -DoutputDirectory=../downloaded_files/
```

Copy the necessary JARs to the Spark JAR directory:

```bash
cp ../downloaded_files/hadoop-aws-3.3.4.jar ../../spark-client/spark-3.5.1-bin-hadoop3/jars/
cp ../downloaded_files/aws-java-sdk-bundle-1.12.262.jar ../../spark-client/spark-3.5.1-bin-hadoop3/jars/
```

---

### 6. 🐳 Start Docker Containers

```bash
docker compose up -d
```

---
### 7. 🪣 Create MinIO Bucket

Access MinIO UI at [http://localhost:9001](http://localhost:9001) or use the CLI:

```bash
mc config host add <ALIAS> <COS-ENDPOINT> <ACCESS-KEY> <SECRET-KEY>
mc config host add minio http://minio:9000/ minio minio123
mc ls minio
mc mb minio/bucket1
```

> ⚠️ If you use a different bucket name, update the `s3-sink.json` file accordingly.

---
### 8. 🌀 Create Kafka Topic

Use the following commands in any Kafka container:

```bash
# Create topic
kafka-topics --create --topic topic1 --bootstrap-server kafka:9092

# List topics
kafka-topics --list --bootstrap-server kafka:9092

# Optional: Delete topic
kafka-topics --delete --topic topic1 --bootstrap-server kafka:9092
```

> ⚠️ If you use a different topic name, update the `s3-sink.json` file accordingly.
--- 

### 9. 💬 Kafka CLI Producer/Consumer

To produce messages manually:

```bash
kafka-console-producer --bootstrap-server kafka:9092 --topic topic1
```

To consume messages:

```bash
kafka-console-consumer --bootstrap-server kafka:9092 --topic topic1
```

---
### 10. 🔌 Register Kafka Connect Sink

This step configures Kafka to write messages to the MinIO bucket:

```bash
curl -X POST -H "Content-Type: application/json" --data @s3-sink.json http://localhost:8083/connectors
```

To delete the connector later:

```bash
curl -X DELETE http://localhost:8083/connectors/s3-sink-connector
```

---
### 11. 📤 Produce Data to Kafka from CSV

From inside the **RHEL container**, run the following:

```bash
cd /scripts
python stream_csv_to_kafka.py --csv_file_path ./csv54304.csv --kafka_topic topic1
```

📄 Output log: `./scripts/minio_transactions_parse_and_analyze.log`

---

### 12. 🔍 Analyze Data with PySpark

Run a PySpark script to load, parse, and filter JSON data from MinIO:

```bash
python minio_transactions_parse_and_analyze.py \
  --access minio \
  --secret minio123 \
  --s3_path "s3a://bucket1/topic1/partition=0/*.json"
```

📄 Output log: `./scripts/stream_csv_to_kafka_example_output.log`

---
## Example Workflow

### Docker Containers

![Docker Architecture](https://github.com/user-attachments/assets/eb48b3a9-88b5-4360-8854-2244913a19e0)>

---

### Streaming Log Example

<details open><summary>Streaming Data</summary>
<p>

```
```

</p>
</details>

---

### MinIO objects after streaming
![MinIO Objects](https://github.com/tomonikolovski/personal_finance_data_pipeline_kafka_spark_minio/assets/10199962/224be657-103f-41f4-a17c-1ea026ecb821)

---

### Using PySpark to parse MinIO objects and perform a simple filtering

<details open><summary>PySpark example</summary>
<p>


```
```

</p>
</details>

---

### Spark Master UI
![Spark Master UI](https://github.com/tomonikolovski/personal_finance_data_pipeline_kafka_spark_minio/assets/10199962/dd227b3d-5d68-4948-9726-baa21dff2d7d)

### Frontend UI
<img width="1391" alt="image" src="https://github.com/user-attachments/assets/f8b714ab-7f53-4a9d-a0a8-3d72a8b750e9" />

### Querying transactions in English language by leveraging local LLM
![Untitled](https://github.com/user-attachments/assets/adf2fb33-0958-4c9a-b879-a47724341449)
