import os
import json
import logging
from flask import Flask, request, jsonify
from confluent_kafka import Producer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.environ.get('KAFKA_TOPIC', 'iot-telemetry-events')

# Configure Kafka Producer
producer_conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'client.id': 'ingestion-api-producer'
}
try:
    producer = Producer(producer_conf)
except Exception as e:
    logger.error(f"Failed to initialize Kafka Producer: {e}")
    producer = None

def delivery_report(err, msg):
    if err is not None:
        logger.error(f'Message delivery failed: {err}')
    else:
        logger.info(f'Message delivered to {msg.topic()} [{msg.partition()}]')

@app.route('/api/v1/telemetry', methods=['POST'])
def ingest_telemetry():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    
    # Required fields based on prompt
    required_fields = ['sensor_id', 'timestamp', 'soil_moisture', 'air_temp', 'air_humidity', 'npk_levels']
    
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        logger.warning(f"Invalid payload: missing {missing_fields}")
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
        
    # Type validation
    try:
        float(data['soil_moisture'])
        float(data['air_temp'])
        float(data['air_humidity'])
    except ValueError:
        logger.warning("Invalid payload: type error")
        return jsonify({"error": "Invalid data types for sensor values"}), 400
        
    # Produce to Kafka
    if producer:
        try:
            # According to guidelines, serialize payload to JSON UTF-8 and use sensor_id as key
            key = str(data['sensor_id']).encode('utf-8')
            value = json.dumps(data).encode('utf-8')
            
            producer.produce(
                topic=KAFKA_TOPIC,
                key=key,
                value=value,
                callback=delivery_report
            )
            # Trigger delivery callbacks asynchronously
            producer.poll(0)
        except Exception as e:
            logger.error(f"Failed to produce message: {e}")
            return jsonify({"error": "Failed to queue message"}), 500
    else:
        logger.warning("Kafka Producer is not initialized. Message not queued.")
    
    logger.info(f"Accepted telemetry from {data['sensor_id']}")
    return jsonify({"status": "Accepted"}), 202

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK"}), 200

if __name__ == '__main__':
    # Typically run via gunicorn, but fallback to flask run for dev
    app.run(host='0.0.0.0', port=5000)
