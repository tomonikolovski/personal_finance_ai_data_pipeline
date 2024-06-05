# personal_data_pipeline_kafka_spark_minio

# Usefull commands
<!-- 
# TO CREATE MINIO BUCKET
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

# DOWNLOAD NECESSARY JARS TO SPARK CLIENT JAR DIRECTORY
cd apache-maven-3.9.7/bin
./mvn dependency:copy-dependencies -DoutputDirectory=../downloaded_files
cd ../../
cp apache-maven-3.9.7/downloaded_files/* spark-client/spark-3.5.1-bin-hadoop3/jars/
mv spark-client/spark-3.5.1-bin-hadoop3/jars/jackson-core-2.10.2.jar spark-client/spark-3.5.1-bin-hadoop3/jars/jackson-core-2.10.2.jar.old


-->