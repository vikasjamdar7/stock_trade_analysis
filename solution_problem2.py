import argparse
import datetime
import json
import logging
import traceback

from confluent_kafka import Producer, Consumer, KafkaError, KafkaException

logging.basicConfig(filename='kafka_consumer.log', level=logging.INFO,
                    format='%(asctime)s ::  %(levelname)s :: %(message)s')
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
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


class Kafka_Consumer_Wrapper:
    def __init__(self):
        conf = {
            'bootstrap.servers': args.broker_host + ":" + args.broker_port,
            'group.id': "consumer_group1",
            'default.topic.config': {'auto.offset.reset': 'smallest'},
            'enable.auto.commit': True
        }
        self.consumer = Consumer(**conf)
        self.consumer.subscribe(['sample_data'])

    def consume_message(self):
        try:
            result = {}
            while True:
                msg = self.consumer.poll(timeout=5.0)
                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        print("result===", result)
                        # End of partition event
                        logger.error('%% %s [%d] reached end at offset %d\n' %
                                     (msg.topic(), msg.partition(), msg.offset()))
                    elif msg.error():
                        raise KafkaException(msg.error())
                else:
                    message = msg.value().decode('utf-8')
                    list_data = json.loads(message)
                    if list_data == "EOM":
                        print("Maximum value for TOTTRDVAL found.")
                        print("result is:")
                        for date_obj in result:
                            print("Date: %s   Max TOTTRDVAL: %s" % (date_obj.strftime('%d-%b-%Y'), result[date_obj]))
                        print("Sending the result on kafka with topic 'result'")
                        producer.produce_message("result", json.dumps(result))
                        break
                    record_date = datetime.datetime.strptime(list_data[10], '%d-%b-%Y')
                    if record_date not in result:
                        result[record_date] = float(list_data[9])
                    else:
                        if result[record_date] < float(list_data[9]):
                            result[record_date] = float(list_data[9])
        except Exception as e:
            logger.error(traceback.format_exc())
        finally:
            # Close down consumer to commit final offsets.
            self.consumer.close()


if __name__ == '__main__':
    consumer = Kafka_Consumer_Wrapper()
    consumer.consume_message()
