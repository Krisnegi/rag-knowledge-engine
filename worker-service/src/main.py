# worker-service/src/main.py
import json
import os
import redis
import sys
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Connect to Redis
# We use 'localhost' for local dev, but in Docker it will be 'rag_redis'
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
QUEUE_NAME = "scraping_queue"

print(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}...")

try:
    client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    client.ping()
    print("✅ Connected to Redis!")
except redis.ConnectionError:
    print("❌ Failed to connect to Redis.")
    sys.exit(1)


def process_job(job_data):
    """
    This function simulates the heavy lifting.
    In Phase 4, we will put Playwright logic here.
    """
    print(f"🚀 Processing Job {job_data.get('jobId')}")
    print(f"🚀 Processing URL: {job_data.get('url')}")
    print(f"   User ID: {job_data.get('userId')}")
    # Simulate work
    import time
    time.sleep(2)
    print("✅ Job Completed!")


def start_worker():
    print(f"👀 Worker listening on queue: '{QUEUE_NAME}'")

    while True:
        # BRPOP blocks execution until a message arrives.
        # It returns a tuple: (queue_name, data)
        # Timeout 0 means wait forever.
        item = client.brpop(QUEUE_NAME, timeout=0)

        if item:
            # item[1] contains the actual data (bytes)
            raw_data = item[1]
            try:
                job_data = json.loads(raw_data)
                process_job(job_data)
            except json.JSONDecodeError:
                print(f"⚠️ Received invalid JSON: {raw_data}")


if __name__ == "__main__":
    start_worker()
