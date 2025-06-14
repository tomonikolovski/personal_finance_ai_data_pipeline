import argparse
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import col
import sys
import socket 

def setup_logger():
    # Configure the logger
    logger = logging.getLogger("S3SparkLogger")
    logger.setLevel(logging.DEBUG)
    
    # Create a console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    
    # Create a formatter and set it for the handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    
    # Add the handler to the logger
    logger.addHandler(ch)
    
    return logger

def transactions_analyzer_default(data_frame, spark):
    try:
        filtered_df = data_frame.filter(col("CAD$") > 0)
        filtered_df.show()
        logger.info("Successfully filtered DataFrame.")
    except Exception as e:
        logger.error("Error filtering DataFrame: {}".format(e))
    finally:
        spark.stop()
        logger.info("Spark session stopped.")


def main():
    try:
        minio_ip = socket.gethostbyname("minio")
        spark = SparkSession.builder \
            .appName("ListFilesOnMinIO") \
            .config("spark.master", "spark://host.docker.internal:7077") \
            .config("spark.hadoop.fs.s3a.access.key", args.access) \
            .config("spark.hadoop.fs.s3a.secret.key", args.secret) \
            .config("spark.hadoop.fs.s3a.endpoint", 'http://{}:9000'.format(minio_ip)) \
            .getOrCreate()
        logger.info("Spark session created successfully.")
    except Exception as e:
        logger.error("Error creating Spark session: {}".format(e))
        sys.exit(1)

    try:
        df = spark.read.json(args.s3_path)
        df.show()
        logger.info("Successfully read JSON from S3 path {}.".format(args.s3_path))
    except Exception as e:
        logger.error("Error reading JSON from S3 path {}: {}".format(args.s3_path, e))
        spark.stop()
        sys.exit(1)

    # transactions_analyzer method here
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process S3 connection details and S3 path.')
    parser.add_argument('--access', required=True, help='S3 Access Key')
    parser.add_argument('--secret', required=True, help='S3 Secret Key')
    parser.add_argument('--s3_path', required=True, help='S3 Path for JSON files')

    args = parser.parse_args()

    logger = setup_logger()

    main()
