import argparse
import csv
import json
import logging
import os
import traceback
from concurrent.futures import ThreadPoolExecutor
from zipfile import ZipFile

from confluent_kafka import Producer

logging.basicConfig(filename='kafka_producer.log', level=logging.INFO,
                    format='%(asctime)s ::  %(levelname)s :: %(message)s')
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument("--max_worker", help="Maximum Threads for creating kafka message", default=3)
parser.add_argument("--csv_folder_path", help="CSV folder path", default='.')
parser.add_argument("--broker_host", help="Kafka broker host IP", default='localhost')
parser.add_argument("--broker_port", help="Kafka broker host port", default='9092')

args = parser.parse_args()


class Kafka_Producer_Wrapper:
    def __init__(self):
        conf = {'bootstrap.servers': args.broker_host + ":" + args.broker_port}
        self.producer = Producer(**conf)

    def produce_message(self, topic, message):
        self.producer.produce(topic, message.encode('utf-8'))
        self.producer.flush()


producer = Kafka_Producer_Wrapper()


def task(csv_file):
    print("Adding messages to kafka for file:", csv_file)
    try:
        with open(csv_file, 'r') as f:
            data = csv.reader(f)
            columns = data.__next__()
            for row in data:
                producer.produce_message('sample_data', json.dumps(row))
    except Exception as e:
        logger.error(traceback.format_exc())


def main():
    try:
        max_workers = int(args.max_worker)
        folder_path = args.csv_folder_path
        file_path_list = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for dir_path, dir_name, file_names in os.walk(folder_path):
                for file_name in file_names:
                    if file_name.endswith('.csv'):
                        file_path = os.path.join(dir_path, file_name)
                        executor.submit(task, file_path)
                        file_path_list.append(file_path)
        print("Sending the last message EOM...")
        producer.produce_message('sample_data', json.dumps("EOM"))
        print("All files data send to Kafka server. Hence Archiving all file to Data.zip")
        print(file_path_list)
        with ZipFile('Data.zip', 'w') as zip:
            # writing each file one by one
            for csv_path in file_path_list:
                zip.write(csv_path)
        for csv_path in file_path_list:
            os.remove(csv_path)
    except Exception as e:
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()
