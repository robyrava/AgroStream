import os
import json
import logging
import psycopg2
from confluent_kafka import Consumer, KafkaException, KafkaError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.environ.get('KAFKA_TOPIC', 'iot-telemetry-events')
KAFKA_GROUP_ID = os.environ.get('KAFKA_GROUP_ID', 'sensor-consumer-group')

DB_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
DB_PORT = os.environ.get('POSTGRES_PORT', '5432')
DB_NAME = os.environ.get('POSTGRES_DB', 'agrostream')
DB_USER = os.environ.get('POSTGRES_USER', 'agro_user')
DB_PASS = os.environ.get('POSTGRES_PASSWORD', 'agro_password')

def get_db_connection():
    import time
    max_retries = 10
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASS
            )
            return conn
        except Exception as e:
            logger.error(f"Error connecting to database (attempt {i+1}/{max_retries}): {e}")
            time.sleep(3)
    return None

def process_message(msg_value):
    try:
        data = json.loads(msg_value.decode('utf-8'))
        return (
            data.get('sensor_id'),
            data.get('timestamp'),
            data.get('soil_moisture'),
            data.get('air_temp'),
            data.get('air_humidity'),
            data.get('npk_levels', {}).get('n'),
            data.get('npk_levels', {}).get('p'),
            data.get('npk_levels', {}).get('k')
        )
    except Exception as e:
        logger.error(f"Error decoding message: {e}")
        return None

def main():
    conf = {
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'group.id': KAFKA_GROUP_ID,
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False
    }

    consumer = Consumer(conf)
    consumer.subscribe([KAFKA_TOPIC])

    logger.info("Starting Kafka Consumer...")
    
    conn = get_db_connection()
    if not conn:
        logger.error("Failed to connect to DB. Exiting.")
        return

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logger.debug(f"Reached end of partition: {msg.topic()} [{msg.partition()}]")
                elif msg.error().code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                    logger.warning("Topic not created yet, waiting...")
                    import time
                    time.sleep(2)
                else:
                    logger.error(f"Kafka error: {msg.error()}")
            else:
                row = process_message(msg.value())
                if row:
                    try:
                        with conn.cursor() as cur:
                            cur.execute("""
                                INSERT INTO sensor_metrics 
                                (sensor_id, timestamp, soil_moisture, air_temp, air_humidity, n_level, p_level, k_level)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """, row)
                        conn.commit()
                        logger.info(f"Inserted metric for sensor {row[0]}")
                        # Commit offset ONLY after successful insert
                        consumer.commit(asynchronous=False)
                    except psycopg2.Error as e:
                        logger.error(f"Database error: {e}")
                        conn.rollback()
                        
    except KeyboardInterrupt:
        logger.info("Aborted by user")
    finally:
        consumer.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    main()
