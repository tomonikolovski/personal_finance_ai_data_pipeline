import csv
from kafka import KafkaProducer
import json

# Kafka configuration
KAFKA_TOPIC = 'topic1'
KAFKA_BROKER = 'kafka:9092'

# Initialize Kafka producer
producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Path to the CSV file
csv_file_path = './csv54304.csv'

# Read CSV file and send messages to Kafka
with open(csv_file_path, mode='r', newline='') as file:
    reader = csv.DictReader(file, quotechar=' ')
    for row in reader:
        producer.send(KAFKA_TOPIC, row)
        print(row)

# Close the producer
producer.flush()
producer.close()
