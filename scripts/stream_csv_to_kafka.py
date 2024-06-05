import csv
from kafka import KafkaProducer
import json
import argparse
import logging
import os

def setup_logging():
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    return logger

def parse_arguments():
    parser = argparse.ArgumentParser(description='Send CSV data to Kafka topic.')
    parser.add_argument('--csv_file_path', required=True, type=str, help='Path to the CSV file')
    parser.add_argument('--kafka_topic', required=True, type=str, help='Kafka topic to send messages to')
    return parser.parse_args()

def main(csv_file_path, kafka_topic):
    try:
        logger.info('Reading CSV file: {}'.format(csv_file_path))
        if not os.path.isfile(csv_file_path):
            logger.error("File not found: {}".format(csv_file_path))
            raise FileNotFoundError("File not found: {}".format(csv_file_path))

        producer = KafkaProducer(
            bootstrap_servers=['kafka:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        with open(csv_file_path, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                producer.send(kafka_topic, row)
                logger.info("Sent row to Kafka topic {}: {}".format(kafka_topic, row))

        producer.flush()
        producer.close()
        logger.info('Finished sending messages to Kafka.')

    except FileNotFoundError as e:
        logger.error(e)
    except Exception as e:
        logger.exception("An error occurred while sending messages to Kafka")

if __name__ == "__main__":
    logger = setup_logging()
    args = parse_arguments()
    main(args.csv_file_path, args.kafka_topic)
