import os
import logging
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

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
        
    # In a real scenario, we would send this to Kafka
    # kafka_host = os.environ.get('KAFKA_HOST', 'localhost:9092')
    # ...
    
    logger.info(f"Accepted telemetry from {data['sensor_id']}")
    return jsonify({"status": "Accepted"}), 202

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK"}), 200

if __name__ == '__main__':
    # Typically run via gunicorn, but fallback to flask run for dev
    app.run(host='0.0.0.0', port=5000)
