import os
import json
from flask import Flask, request, jsonify
from confluent_kafka import Producer

app = Flask(__name__)

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.environ.get('KAFKA_TOPIC', 'telemetry_data')

producer_conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'client.id': 'flask-ingestion-api'
}
producer = Producer(producer_conf)

def delivery_report(err, msg):
    """ Called once for each message produced to indicate delivery result. """
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/ingest', methods=['POST'])
def ingest_data():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON payload"}), 400
        
        # Simple validation: ensure sensor_id exists
        if 'sensor_id' not in data:
            return jsonify({"error": "Missing sensor_id"}), 400

        # Asynchronously produce message to Kafka
        producer.produce(
            topic=KAFKA_TOPIC,
            key=str(data['sensor_id']).encode('utf-8'),
            value=json.dumps(data).encode('utf-8'),
            callback=delivery_report
        )
        producer.poll(0) # trigger delivery callbacks
        
        return jsonify({"status": "accepted"}), 202

    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Typically run via Gunicorn in production, this is for local testing fallback
    app.run(host='0.0.0.0', port=5000)
