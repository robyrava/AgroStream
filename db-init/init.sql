CREATE TABLE IF NOT EXISTS sensor_metrics (
    id SERIAL PRIMARY KEY,
    sensor_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    soil_moisture REAL,
    air_temp REAL,
    air_humidity REAL,
    n_level REAL,
    p_level REAL,
    k_level REAL
);

CREATE INDEX IF NOT EXISTS idx_sensor_metrics_timestamp ON sensor_metrics (timestamp);
