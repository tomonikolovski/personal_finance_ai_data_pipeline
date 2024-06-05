from kafka import KafkaConsumer
import json

# Initialize the Kafka consumer
consumer = KafkaConsumer(
    'topic1',
    bootstrap_servers='kafka:9092',
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# Consume data from Kafka
def consume_data():
    for message in consumer:
        print(f'Received: {message.value}')

if __name__ == '__main__':
    consume_data()

