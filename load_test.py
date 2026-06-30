import asyncio
import aiohttp
import json
import random
import time
from datetime import datetime, timezone

import os
URL = os.environ.get("API_URL", "http://ingestion-api:5000/api/v1/telemetry")
NUM_REQUESTS = 3000
CONCURRENCY = 150

async def send_request(session, req_id):
    payload = {
        "sensor_id": f"sensor-{random.randint(1, 100)}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "soil_moisture": round(random.uniform(10.0, 60.0), 2),
        "air_temp": round(random.uniform(15.0, 40.0), 2),
        "air_humidity": round(random.uniform(30.0, 95.0), 2),
        "npk_levels": {
            "n": random.randint(10, 50),
            "p": random.randint(10, 50),
            "k": random.randint(10, 50)
        }
    }
    
    try:
        async with session.post(URL, json=payload, headers={'Content-Type': 'application/json'}, timeout=5) as response:
            return response.status
    except Exception as e:
        return type(e).__name__

async def worker(queue, session, results):
    while True:
        req_id = await queue.get()
        status = await send_request(session, req_id)
        results[status] = results.get(status, 0) + 1
        queue.task_done()

async def main():
    queue = asyncio.Queue()
    results = {}
    
    for i in range(NUM_REQUESTS):
        queue.put_nowait(i)
        
    async with aiohttp.ClientSession() as session:
        tasks = []
        for _ in range(CONCURRENCY):
            task = asyncio.create_task(worker(queue, session, results))
            tasks.append(task)
            
        print(f"Starting load test: sending {NUM_REQUESTS} requests with concurrency {CONCURRENCY}...")
        start_time = time.time()
        
        await queue.join()
        
        end_time = time.time()
        
        for task in tasks:
            task.cancel()
            
    print(f"\n--- Load Test Results ---")
    print(f"Total Requests: {NUM_REQUESTS}")
    print(f"Time Taken: {end_time - start_time:.2f} seconds")
    print(f"Throughput: {NUM_REQUESTS / (end_time - start_time):.2f} req/s")
    print("Responses:")
    for status, count in results.items():
        print(f"  {status}: {count}")

if __name__ == "__main__":
    asyncio.run(main())
