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

```python
root@5ef8991ff11c:/scripts# python stream_csv_to_kafka.py --csv_file_path ./csv54304.csv --kafka_topic topic1
2024-06-05 16:42:53,363 - INFO - Reading CSV file: ./csv54304.csv
2024-06-05 16:42:53,368 - INFO - <BrokerConnection node_id=bootstrap-0 host=kafka:9092 <connecting> [IPv4 ('172.19.0.6', 9092)]>: connecting to kafka:9092 [('172.19.0.6', 9092) IPv4]
2024-06-05 16:42:53,369 - INFO - Probing node bootstrap-0 broker version
2024-06-05 16:42:53,370 - INFO - <BrokerConnection node_id=bootstrap-0 host=kafka:9092 <connecting> [IPv4 ('172.19.0.6', 9092)]>: Connection complete.
2024-06-05 16:42:53,477 - INFO - Broker version identified as 2.5.0
2024-06-05 16:42:53,477 - INFO - Set configuration api_version=(2, 5, 0) to skip auto check_version requests on startup
2024-06-05 16:42:53,487 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/15/2024', 'Cheque Number': '', 'Description 1': 'COMPANY1', 'Description 2': '', 'CAD$': '-65.54', 'USD$': ''}
2024-06-05 16:42:53,488 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/15/2024', 'Cheque Number': '', 'Description 1': 'COMPANY2', 'Description 2': '', 'CAD$': '-4', 'USD$': ''}
2024-06-05 16:42:53,489 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/15/2024', 'Cheque Number': '', 'Description 1': 'COMPANY3', 'Description 2': '', 'CAD$': '-1.73', 'USD$': ''}
2024-06-05 16:42:53,490 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/15/2024', 'Cheque Number': '', 'Description 1': 'COMPANY4', 'Description 2': '', 'CAD$': '-20.28', 'USD$': ''}
2024-06-05 16:42:53,490 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/18/2024', 'Cheque Number': '', 'Description 1': 'COMPANY5', 'Description 2': '', 'CAD$': '-12.18', 'USD$': ''}
2024-06-05 16:42:53,490 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/19/2024', 'Cheque Number': '', 'Description 1': 'COMPANY6', 'Description 2': '', 'CAD$': '-4', 'USD$': ''}
2024-06-05 16:42:53,493 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/19/2024', 'Cheque Number': '', 'Description 1': 'COMPANY7', 'Description 2': '', 'CAD$': '-29.38', 'USD$': ''}
2024-06-05 16:42:53,493 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/20/2024', 'Cheque Number': '', 'Description 1': 'COMPANY8', 'Description 2': '', 'CAD$': '-111.87', 'USD$': ''}
2024-06-05 16:42:53,494 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/20/2024', 'Cheque Number': '', 'Description 1': 'COMPANY9', 'Description 2': '', 'CAD$': '-53.17', 'USD$': ''}
2024-06-05 16:42:53,494 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/21/2024', 'Cheque Number': '', 'Description 1': 'COMPANY10', 'Description 2': '', 'CAD$': '-20.34', 'USD$': ''}
2024-06-05 16:42:53,494 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/21/2024', 'Cheque Number': '', 'Description 1': 'COMPANY11', 'Description 2': '', 'CAD$': '-34.72', 'USD$': ''}
2024-06-05 16:42:53,494 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/22/2024', 'Cheque Number': '', 'Description 1': 'COMPANY12', 'Description 2': '', 'CAD$': '-4', 'USD$': ''}
2024-06-05 16:42:53,494 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/22/2024', 'Cheque Number': '', 'Description 1': 'COMPANY13', 'Description 2': '', 'CAD$': '-20.28', 'USD$': ''}
2024-06-05 16:42:53,495 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/24/2024', 'Cheque Number': '', 'Description 1': 'COMPANY14', 'Description 2': '', 'CAD$': '-1.73', 'USD$': ''}
2024-06-05 16:42:53,495 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/24/2024', 'Cheque Number': '', 'Description 1': 'COMPANY15', 'Description 2': '', 'CAD$': '-20.28', 'USD$': ''}
2024-06-05 16:42:53,495 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/25/2024', 'Cheque Number': '', 'Description 1': 'COMPANY16', 'Description 2': '', 'CAD$': '-8.07', 'USD$': ''}
2024-06-05 16:42:53,496 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/25/2024', 'Cheque Number': '', 'Description 1': 'COMPANY17', 'Description 2': '', 'CAD$': '-124.81', 'USD$': ''}
2024-06-05 16:42:53,496 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/25/2024', 'Cheque Number': '', 'Description 1': 'COMPANY18', 'Description 2': '', 'CAD$': '-20.28', 'USD$': ''}
2024-06-05 16:42:53,496 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/26/2024', 'Cheque Number': '', 'Description 1': 'COMPANY19', 'Description 2': '', 'CAD$': '-4', 'USD$': ''}
2024-06-05 16:42:53,496 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/27/2024', 'Cheque Number': '', 'Description 1': 'COMPANY20', 'Description 2': '', 'CAD$': '-84.75', 'USD$': ''}
2024-06-05 16:42:53,497 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/28/2024', 'Cheque Number': '', 'Description 1': 'COMPANY21', 'Description 2': '', 'CAD$': '-58.08', 'USD$': ''}
2024-06-05 16:42:53,497 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/28/2024', 'Cheque Number': '', 'Description 1': 'COMPANY22', 'Description 2': '', 'CAD$': '111.87', 'USD$': ''}
2024-06-05 16:42:53,497 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/28/2024', 'Cheque Number': '', 'Description 1': 'COMPANY23', 'Description 2': '', 'CAD$': '-51.15', 'USD$': ''}
2024-06-05 16:42:53,497 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/28/2024', 'Cheque Number': '', 'Description 1': 'COMPANY24', 'Description 2': '', 'CAD$': '-12.86', 'USD$': ''}
2024-06-05 16:42:53,498 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/29/2024', 'Cheque Number': '', 'Description 1': 'COMPANY25', 'Description 2': '', 'CAD$': '-4', 'USD$': ''}
2024-06-05 16:42:53,498 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/29/2024', 'Cheque Number': '', 'Description 1': 'COMPANY26', 'Description 2': '', 'CAD$': '-10.14', 'USD$': ''}
2024-06-05 16:42:53,498 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '4/29/2024', 'Cheque Number': '', 'Description 1': 'COMPANY27', 'Description 2': '', 'CAD$': '-10.14', 'USD$': ''}
2024-06-05 16:42:53,498 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/1/2024', 'Cheque Number': '', 'Description 1': 'COMPANY28', 'Description 2': '', 'CAD$': '0.68', 'USD$': ''}
2024-06-05 16:42:53,498 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/2/2024', 'Cheque Number': '', 'Description 1': 'COMPANY29', 'Description 2': '', 'CAD$': '-10.14', 'USD$': ''}
2024-06-05 16:42:53,498 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/2/2024', 'Cheque Number': '', 'Description 1': 'COMPANY30', 'Description 2': '', 'CAD$': '-10.14', 'USD$': ''}
2024-06-05 16:42:53,499 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/3/2024', 'Cheque Number': '', 'Description 1': 'COMPANY31', 'Description 2': '', 'CAD$': '-4', 'USD$': ''}
2024-06-05 16:42:53,499 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/3/2024', 'Cheque Number': '', 'Description 1': 'COMPANY32', 'Description 2': '', 'CAD$': '-2.24', 'USD$': ''}
2024-06-05 16:42:53,499 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/3/2024', 'Cheque Number': '', 'Description 1': 'COMPANY33', 'Description 2': '', 'CAD$': '-7.22', 'USD$': ''}
2024-06-05 16:42:53,500 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/3/2024', 'Cheque Number': '', 'Description 1': 'COMPANY34', 'Description 2': '', 'CAD$': '-11.3', 'USD$': ''}
2024-06-05 16:42:53,500 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/3/2024', 'Cheque Number': '', 'Description 1': 'COMPANY35', 'Description 2': '', 'CAD$': '-59.71', 'USD$': ''}
2024-06-05 16:42:53,500 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/4/2024', 'Cheque Number': '', 'Description 1': 'COMPANY36', 'Description 2': '', 'CAD$': '-8.56', 'USD$': ''}
2024-06-05 16:42:53,500 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/4/2024', 'Cheque Number': '', 'Description 1': 'COMPANY37', 'Description 2': '', 'CAD$': '-88', 'USD$': ''}
2024-06-05 16:42:53,501 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/4/2024', 'Cheque Number': '', 'Description 1': 'COMPANY38', 'Description 2': '', 'CAD$': '-38.08', 'USD$': ''}
2024-06-05 16:42:53,501 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/5/2024', 'Cheque Number': '', 'Description 1': 'COMPANY39', 'Description 2': '', 'CAD$': '-14.59', 'USD$': ''}
2024-06-05 16:42:53,501 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/5/2024', 'Cheque Number': '', 'Description 1': 'COMPANY40', 'Description 2': '', 'CAD$': '-33.89', 'USD$': ''}
2024-06-05 16:42:53,501 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/5/2024', 'Cheque Number': '', 'Description 1': 'COMPANY41', 'Description 2': '', 'CAD$': '9400', 'USD$': ''}
2024-06-05 16:42:53,502 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/6/2024', 'Cheque Number': '', 'Description 1': 'COMPANY42', 'Description 2': '', 'CAD$': '-4', 'USD$': ''}
2024-06-05 16:42:53,504 - INFO - <BrokerConnection node_id=1 host=kafka:9092 <connecting> [IPv4 ('172.19.0.6', 9092)]>: connecting to kafka:9092 [('172.19.0.6', 9092) IPv4]
2024-06-05 16:42:53,505 - INFO - <BrokerConnection node_id=1 host=kafka:9092 <connecting> [IPv4 ('172.19.0.6', 9092)]>: Connection complete.
2024-06-05 16:42:53,505 - INFO - <BrokerConnection node_id=bootstrap-0 host=kafka:9092 <connected> [IPv4 ('172.19.0.6', 9092)]>: Closing connection. 
2024-06-05 16:42:53,504 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/7/2024', 'Cheque Number': '', 'Description 1': 'COMPANY43', 'Description 2': '', 'CAD$': '-1.31', 'USD$': ''}
2024-06-05 16:42:53,507 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/7/2024', 'Cheque Number': '', 'Description 1': 'COMPANY44', 'Description 2': '', 'CAD$': '-9.99', 'USD$': ''}
2024-06-05 16:42:53,508 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/7/2024', 'Cheque Number': '', 'Description 1': 'COMPANY45', 'Description 2': '', 'CAD$': '-20.28', 'USD$': ''}
2024-06-05 16:42:53,509 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/8/2024', 'Cheque Number': '', 'Description 1': 'COMPANY46', 'Description 2': '', 'CAD$': '-19.39', 'USD$': ''}
2024-06-05 16:42:53,510 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/8/2024', 'Cheque Number': '', 'Description 1': 'COMPANY47', 'Description 2': '', 'CAD$': '-20.28', 'USD$': ''}
2024-06-05 16:42:53,510 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/10/2024', 'Cheque Number': '', 'Description 1': 'COMPANY48', 'Description 2': '', 'CAD$': '-4', 'USD$': ''}
2024-06-05 16:42:53,510 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/10/2024', 'Cheque Number': '', 'Description 1': 'COMPANY49', 'Description 2': '', 'CAD$': '-10.14', 'USD$': ''}
2024-06-05 16:42:53,510 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/10/2024', 'Cheque Number': '', 'Description 1': 'COMPANY50', 'Description 2': '', 'CAD$': '-10.14', 'USD$': ''}
2024-06-05 16:42:53,511 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/12/2024', 'Cheque Number': '', 'Description 1': 'COMPANY51', 'Description 2': '', 'CAD$': '-1.3', 'USD$': ''}
2024-06-05 16:42:53,511 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/12/2024', 'Cheque Number': '', 'Description 1': 'COMPANY52', 'Description 2': '', 'CAD$': '-29.92', 'USD$': ''}
2024-06-05 16:42:53,511 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/12/2024', 'Cheque Number': '', 'Description 1': 'COMPANY53', 'Description 2': '', 'CAD$': '-39.93', 'USD$': ''}
2024-06-05 16:42:53,511 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/12/2024', 'Cheque Number': '', 'Description 1': 'COMPANY54', 'Description 2': '', 'CAD$': '-18.08', 'USD$': ''}
2024-06-05 16:42:53,511 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/13/2024', 'Cheque Number': '', 'Description 1': 'COMPANY55', 'Description 2': '', 'CAD$': '-3.38', 'USD$': ''}
2024-06-05 16:42:53,512 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/13/2024', 'Cheque Number': '', 'Description 1': 'COMPANY56', 'Description 2': '', 'CAD$': '-4', 'USD$': ''}
2024-06-05 16:42:53,512 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/13/2024', 'Cheque Number': '', 'Description 1': 'COMPANY57', 'Description 2': '', 'CAD$': '-16.76', 'USD$': ''}
2024-06-05 16:42:53,512 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/13/2024', 'Cheque Number': '', 'Description 1': 'COMPANY58', 'Description 2': '', 'CAD$': '-42.92', 'USD$': ''}
2024-06-05 16:42:53,512 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/14/2024', 'Cheque Number': '', 'Description 1': 'COMPANY59', 'Description 2': '', 'CAD$': '-29.38', 'USD$': ''}
2024-06-05 16:42:53,512 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/14/2024', 'Cheque Number': '', 'Description 1': 'COMPANY60', 'Description 2': '', 'CAD$': '-34.91', 'USD$': ''}
2024-06-05 16:42:53,513 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/15/2024', 'Cheque Number': '', 'Description 1': 'COMPANY61', 'Description 2': '', 'CAD$': '-10.14', 'USD$': ''}
2024-06-05 16:42:53,513 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/15/2024', 'Cheque Number': '', 'Description 1': 'COMPANY62', 'Description 2': '', 'CAD$': '-10.14', 'USD$': ''}
2024-06-05 16:42:53,513 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/16/2024', 'Cheque Number': '', 'Description 1': 'COMPANY63', 'Description 2': '', 'CAD$': '-54.79', 'USD$': ''}
2024-06-05 16:42:53,513 - INFO - Sent row to Kafka topic topic1: {'Account Type': 'Visa', 'Account Number': '1.23457E+14', 'Transaction Date': '5/16/2024', 'Cheque Number': '', 'Description 1': 'COMPANY64', 'Description 2': '', 'CAD$': '-1.73', 'USD$': ''}
2024-06-05 16:42:53,541 - INFO - Closing the Kafka producer with 9223372036.0 secs timeout.
2024-06-05 16:42:53,542 - INFO - <BrokerConnection node_id=1 host=kafka:9092 <connected> [IPv4 ('172.19.0.6', 9092)]>: Closing connection. 
2024-06-05 16:42:53,543 - INFO - Finished sending messages to Kafka.
root@5ef8991ff11c:/scripts# 
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


```python
root@5ef8991ff11c:/scripts# python minio_transactions_parse_and_analyze.py --access minio --secret minio123 --endpoint "http://172.19.0.4:9000" --s3_path "s3a://bucket1/topic1/partition=0/*.json"
SLF4J: Class path contains multiple SLF4J bindings.
SLF4J: Found binding in [jar:file:/opt/spark/spark-3.5.1-bin-hadoop3/jars/slf4j-reload4j-1.7.36.jar!/org/slf4j/impl/StaticLoggerBinder.class]
SLF4J: Found binding in [jar:file:/opt/spark/spark-3.5.1-bin-hadoop3/jars/logback-classic-1.2.10.jar!/org/slf4j/impl/StaticLoggerBinder.class]
SLF4J: See http://www.slf4j.org/codes.html#multiple_bindings for an explanation.
SLF4J: Actual binding is of type [org.slf4j.impl.Reload4jLoggerFactory]
log4j:WARN No appenders could be found for logger (org.apache.spark.util.ShutdownHookManager).
log4j:WARN Please initialize the log4j system properly.
log4j:WARN See http://logging.apache.org/log4j/1.2/faq.html#noconfig for more info.
2024-06-05 16:47:04,909 - S3SparkLogger - INFO - Spark session created successfully.
+--------------+------------+-------+-------------+-------------+-------------+----------------+----+
|Account Number|Account Type|   CAD$|Cheque Number|Description 1|Description 2|Transaction Date|USD$|
+--------------+------------+-------+-------------+-------------+-------------+----------------+----+
|   1.23457E+14|        Visa|-124.81|             |    COMPANY17|             |       4/25/2024|    |
|   1.23457E+14|        Visa|-111.87|             |     COMPANY8|             |       4/20/2024|    |
|   1.23457E+14|        Visa| -20.34|             |    COMPANY10|             |       4/21/2024|    |
|   1.23457E+14|        Visa| -34.72|             |    COMPANY11|             |       4/21/2024|    |
|   1.23457E+14|        Visa| -20.28|             |    COMPANY13|             |       4/22/2024|    |
|   1.23457E+14|        Visa| -20.28|             |    COMPANY15|             |       4/24/2024|    |
|   1.23457E+14|        Visa| -20.28|             |    COMPANY18|             |       4/25/2024|    |
|   1.23457E+14|        Visa| -84.75|             |    COMPANY20|             |       4/27/2024|    |
|   1.23457E+14|        Visa| -58.08|             |    COMPANY21|             |       4/28/2024|    |
|   1.23457E+14|        Visa| 111.87|             |    COMPANY22|             |       4/28/2024|    |
|   1.23457E+14|        Visa| -51.15|             |    COMPANY23|             |       4/28/2024|    |
|   1.23457E+14|        Visa| -12.86|             |    COMPANY24|             |       4/28/2024|    |
|   1.23457E+14|        Visa| -10.14|             |    COMPANY26|             |       4/29/2024|    |
|   1.23457E+14|        Visa| -10.14|             |    COMPANY27|             |       4/29/2024|    |
|   1.23457E+14|        Visa| -10.14|             |    COMPANY49|             |       5/10/2024|    |
|   1.23457E+14|        Visa| -10.14|             |    COMPANY50|             |       5/10/2024|    |
|   1.23457E+14|        Visa| -29.92|             |    COMPANY52|             |       5/12/2024|    |
|   1.23457E+14|        Visa| -39.93|             |    COMPANY53|             |       5/12/2024|    |
|   1.23457E+14|        Visa| -18.08|             |    COMPANY54|             |       5/12/2024|    |
|   1.23457E+14|        Visa| -16.76|             |    COMPANY57|             |       5/13/2024|    |
+--------------+------------+-------+-------------+-------------+-------------+----------------+----+
only showing top 20 rows

2024-06-05 16:47:18,111 - S3SparkLogger - INFO - Successfully read JSON from S3 path s3a://bucket1/topic1/partition=0/*.json.
+--------------+------------+------+-------------+-------------+-------------+----------------+----+
|Account Number|Account Type|  CAD$|Cheque Number|Description 1|Description 2|Transaction Date|USD$|
+--------------+------------+------+-------------+-------------+-------------+----------------+----+
|   1.23457E+14|        Visa|111.87|             |    COMPANY22|             |       4/28/2024|    |
|   1.23457E+14|        Visa|  9400|             |    COMPANY41|             |        5/5/2024|    |
+--------------+------------+------+-------------+-------------+-------------+----------------+----+

2024-06-05 16:47:19,469 - S3SparkLogger - INFO - Successfully filtered DataFrame.
2024-06-05 16:47:19,657 - S3SparkLogger - INFO - Spark session stopped.
```

</p>
</details>

---

### Spark Master UI
![Spark Master UI](https://github.com/tomonikolovski/personal_finance_data_pipeline_kafka_spark_minio/assets/10199962/dd227b3d-5d68-4948-9726-baa21dff2d7d)

### Frontend UI
<img width="1391" alt="image" src="https://github.com/user-attachments/assets/f8b714ab-7f53-4a9d-a0a8-3d72a8b750e9" />


