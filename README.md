# personal_data_pipeline_kafka_spark_minio

# Usefull commands
<!-- 
mc config host add <ALIAS> <COS-ENDPOINT> <ACCESS-KEY> <SECRET-KEY>
mc config host add minio http://minio:9000/ minio minio123
mc ls minio
mc mb minio/bucket1

curl -X POST -H "Content-Type: application/json" --data @s3-sink.json http://localhost:8083/connectors
curl -X DELETE http://localhost:8083/connectors/s3-sink-connector

kafka-topics --list --bootstrap-server kafka:9092
kafka-topics --create --topic testtopic --bootstrap-server kafka:9092
kafka-topics --delete --topic testtopic --bootstrap-server kafka:9092

kafka-console-producer --broker-list kafka:9092 --topic testtopic
kafka-console-consumer --broker-list kafka:9092 --topic testtopic 
-->