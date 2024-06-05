# Personal Data Pipeline with Kafka, MinIO and Spark3

# Usefull commands

# Create MinIO Bucket
mc config host add <ALIAS> <COS-ENDPOINT> <ACCESS-KEY> <SECRET-KEY>
mc config host add minio http://minio:9000/ minio minio123
mc ls minio
mc mb minio/bucket1

# CREATE KAFKA CONNECT CONNECTOR FOR MINIO. NEEDS TO BE DONE EVERY TIME THE CONTAINER IS RE-CREATED
curl -X POST -H "Content-Type: application/json" --data @s3-sink.json http://localhost:8083/connectors
curl -X DELETE http://localhost:8083/connectors/s3-sink-connector

# CREATE KAFKA TOPIC
kafka-topics --list --bootstrap-server kafka:9092
kafka-topics --delete --topic topic1 --bootstrap-server kafka:9092
kafka-topics --create --topic topic1 --bootstrap-server kafka:9092
kafka-topics --list --bootstrap-server kafka:9092

kafka-console-producer --bootstrap-server kafka:9092 --topic topic1
kafka-console-consumer --bootstrap-server kafka:9092 --topic topic1 

# EXAMPLE TRANSACTION
{"Account Type": "Visa", "Account Number": "1.23457E+14", "Transaction Date": "5/16/2024", "Cheque Number": "", "Description 1": "COMPANY64", "Description 2": "", "CAD$": "-1.73", "USD$": ""}

# DOWNLOAD JAVA
https://download.oracle.com/java/22/latest/jdk-22_linux-x64_bin.tar.gz
untar and place it into spark-client directory

# DOWNLOAD SPARK CLIENT
https://archive.apache.org/dist/spark/spark-3.5.1/spark-3.5.1-bin-hadoop3.tgz
untar and place it into spark-client directory

# DOWNLOAD NECESSARY JARS TO SPARK CLIENT JAR DIRECTORY
cd apache-maven-3.9.7/bin
./mvn dependency:copy-dependencies -DoutputDirectory=../downloaded_files
cd ../../
cp apache-maven-3.9.7/downloaded_files/* spark-client/spark-3.5.1-bin-hadoop3/jars/
mv spark-client/spark-3.5.1-bin-hadoop3/jars/jackson-core-2.10.2.jar spark-client/spark-3.5.1-bin-hadoop3/jars/jackson-core-2.10.2.jar.old

# RUN THE PYSPARK SCRIPT
python read_from_minio.py --access minio --secret minio123 --endpoint "http://172.19.0.4:9000" --s3_path "s3a://bucket1/topic1/partition=0/*.json"
