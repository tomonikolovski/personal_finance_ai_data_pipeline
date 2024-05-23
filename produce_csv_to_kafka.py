import csv
from kafka import KafkaProducer
import json

# Kafka configuration
KAFKA_TOPIC = 'test-topic'
KAFKA_BROKER = 'localhost:9092'

# Initialize Kafka producer
producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Path to the CSV file
csv_file_path = '/mnt/c/Users/tomas/Downloads/csv54304.csv'

# Read CSV file and send messages to Kafka
with open(csv_file_path, mode='r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        producer.send(KAFKA_TOPIC, row)
        print(f'Sent: {row}')

# Close the producer
producer.flush()
producer.close()
