import json
import os
import sys
import redis
import psycopg2
from google import genai
from google.genai import types
from pinecone import Pinecone
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

# --- Configuration ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
QUEUE_NAME = "scraping_queue"
DB_URL = os.getenv("DATABASE_URL")

# AI Config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

# Initialize Clients
client = genai.Client(api_key=GEMINI_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

# --- Database Helpers ---


def get_db_connection():
    return psycopg2.connect(DB_URL)


def update_job_status(job_id, status):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE \"Document\" SET status = %s, updated_at = NOW() WHERE id = %s",
            (status, job_id)
        )
        conn.commit()
        cur.close()
        conn.close()
        print(f"🔄 Job {job_id} updated to {status}")
    except Exception as e:
        print(f"❌ DB Error: {e}")

# --- Core Logic ---


def scrape_url(url):
    """Scrapes text from a URL"""
    print(f"🕷️ Scraping: {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000)
        content = page.content()
        browser.close()

        soup = BeautifulSoup(content, "html.parser")
        for script in soup(["script", "style"]):
            script.extract()
        text = soup.get_text(separator=' ', strip=True)
        return text


def chunk_text(text):
    """Splits text into chunks of 1000 characters with 200 overlap"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_text(text)
    print(f"🔪 Sliced text into {len(chunks)} chunks")
    return chunks


def generate_embedding(text):
    """Calls Gemini to get a vector (768 numbers)"""
    result = client.models.embed_content(
        model="text-embedding-004",
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
    )
    return result.embeddings[0].values


def process_job(job_data):
    job_id = job_data.get('jobId')
    url = job_data.get('url')

    if not job_id or not url:
        return

    print(f"🚀 Processing Job {job_id}")

    try:
        update_job_status(job_id, 'IN_PROGRESS')

        # 1. Scrape
        raw_text = scrape_url(url)

        # 2. Chunk
        chunks = chunk_text(raw_text)

        # 3. Embed & Upload to Pinecone
        vectors = []
        for i, chunk in enumerate(chunks):
            vector = generate_embedding(chunk)

            # Prepare data for Pinecone
            # ID format: "job_id#chunk_index" (e.g., "abc-123#0", "abc-123#1")
            vectors.append({
                "id": f"{job_id}#{i}",
                "values": vector,
                "metadata": {
                    "text": chunk,  # We store the actual text so we can retrieve it later!
                    "source_url": url,
                    "job_id": job_id
                }
            })

        # Batch upload to Pinecone
        if vectors:
            index.upsert(vectors=vectors)
            print(f"💾 Uploaded {len(vectors)} vectors to Pinecone")

        update_job_status(job_id, 'COMPLETED')

    except Exception as e:
        print(f"❌ Job Failed: {e}")
        update_job_status(job_id, 'FAILED')

# --- Worker Loop ---


def start_worker():
    print(f"👀 Worker listening on queue: '{QUEUE_NAME}'")
    client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

    while True:
        item = client.brpop(QUEUE_NAME, timeout=0)
        if item:
            try:
                job_data = json.loads(item[1])
                process_job(job_data)
            except Exception as e:
                print(f"⚠️ Error: {e}")


if __name__ == "__main__":
    start_worker()
