# Personal Data Pipeline with Kafka, MinIO and Spark3

1. Clone the repo
2. Download and untar java into the spark-client directory spark-client/jdk-22.0.1 - https://download.oracle.com/java/22/latest/jdk-22_linucdx-x64_bin.tar.gz
3. Download and untar spark3 into the spark-client directory spark-client/spark-3.5.1-bin-hadoop3 - https://archive.apache.org/dist/spark/spark-3.5.1/spark-3.5.1-bin-hadoop3.tgz
4. Download additional Jar files to be able to interract with MinIO buckets from PySpark
    - Pre-compiled Maven already present under apache-maven-3.9.7
    - pom.xml with all neccessary repos set up already 
    - cd apache-maven-3.9.7/bin and run ./mvn dependency:copy-dependencies -DoutputDirectory=../downloaded_files/
    - copy the files - cp apache-maven-3.9.7/downloaded_files/* spark-client/spark-3.5.1-bin-hadoop3/jars/
5. Start the containers with docker compose up -d
6. Create a MinIO bucket by navigating to http://localhost:9001/ or by using the CLI. Call it "bucket1" or anything else, but then make sure to update the s3-sink.json
mc config host add <ALIAS> <COS-ENDPOINT> <ACCESS-KEY> <SECRET-KEY>
mc config host add minio http://minio:9000/ minio minio123
mc ls minio
mc mb minio/bucket1

7. Create Kafka topic. Name it "topic1" or anything else, but then make sure to update the s3-sink.json file. Delete command attached just in a case.
kafka-topics --list --bootstrap-server kafka:9092
kafka-topics --delete --topic topic1 --bootstrap-server kafka:9092
kafka-topics --create --topic topic1 --bootstrap-server kafka:9092
kafka-topics --list --bootstrap-server kafka:9092

8. Kafka commands to consume and produce via the CLI
kafka-console-producer --bootstrap-server kafka:9092 --topic topic1
kafka-console-consumer --bootstrap-server kafka:9092 --topic topic1 

9. Publish the Kafka Connect sink configuration for the MinIO bucket. This enables Kafka to write the data to the MinIO bucket
curl -X POST -H "Content-Type: application/json" --data @s3-sink.json http://localhost:8083/connectors

10. If you need to delete later on - curl -X DELETE http://localhost:8083/connectors/s3-sink-connector

11. Run a script to produce data to topic1. From the RHEL container navigate to /scripts and run
python produce_csv_to_kafka.py - This will publish the contents of the csv file to topic1

12. Run a PySpark script to parse all saved json transactions, save them in a DataFrame and run a simple filter over it. For some reason minio:9000 is not resolving properly and we need to use the container IP instead.
python minio_transactions_parse_and_analyze.py --access minio --secret minio123 --endpoint "http://172.19.0.4:9000" --s3_path "s3a://bucket1/topic1/partition=0/*.json"

