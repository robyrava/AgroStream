import os
import json
import time
import psycopg2
from psycopg2 import sql
from confluent_kafka import Consumer, KafkaError

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.environ.get('KAFKA_TOPIC', 'telemetry_data')
KAFKA_GROUP_ID = os.environ.get('KAFKA_GROUP_ID', 'agrostream_consumer_group')

POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = os.environ.get('POSTGRES_PORT', '5432')
POSTGRES_USER = os.environ.get('POSTGRES_USER', 'agro_user')
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'agro_password')
POSTGRES_DB = os.environ.get('POSTGRES_DB', 'agrostream')

def init_db():
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB
    )
    cur = conn.cursor()
    # Create table if it doesn't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id SERIAL PRIMARY KEY,
            sensor_id VARCHAR(255) NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            soil_moisture FLOAT,
            air_temperature FLOAT,
            nitrogen FLOAT,
            phosphorus FLOAT,
            potassium FLOAT
        )
    """)
    conn.commit()
    return conn, cur

def start_consumer():
    # Wait for dependent services to be ready
    time.sleep(10)
    
    conn, cur = init_db()

    consumer_conf = {
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'group.id': KAFKA_GROUP_ID,
        'auto.offset.reset': 'earliest'
    }
    
    consumer = Consumer(consumer_conf)
    consumer.subscribe([KAFKA_TOPIC])

    print("Started Kafka Consumer. Waiting for messages...")

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(msg.error())
                    break

            # Process message
            payload = json.loads(msg.value().decode('utf-8'))
            print(f"Received message: {payload}")

            # Insert into database
            try:
                cur.execute(
                    """
                    INSERT INTO telemetry (sensor_id, soil_moisture, air_temperature, nitrogen, phosphorus, potassium)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        payload.get('sensor_id'),
                        payload.get('soil_moisture'),
                        payload.get('air_temperature'),
                        payload.get('nitrogen'),
                        payload.get('phosphorus'),
                        payload.get('potassium')
                    )
                )
                conn.commit()
            except Exception as e:
                print(f"Database error: {e}")
                conn.rollback()

    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()
        cur.close()
        conn.close()

if __name__ == '__main__':
    start_consumer()
