import asyncio
import json
import os
import redis
import psycopg2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Import our modular logic
from src.rag_engine import search_pinecone, generate_answer, get_embedding
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

# --- Config & DB Helpers ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
QUEUE_NAME = "scraping_queue"
DB_URL = os.getenv("DATABASE_URL")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)


def update_job_status(job_id, status):
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute(
            "UPDATE \"Document\" SET status = %s, updated_at = NOW() WHERE id = %s", (status, job_id))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ DB Error: {e}")

# --- Scraping Logic (Kept here for now, or move to scraper.py optionally) ---


def process_scraping_job(job_data):
    """The heavy lifting background task"""
    job_id = job_data.get('jobId')
    url = job_data.get('url')
    print(f"🚀 Processing Job {job_id}")

    try:
        update_job_status(job_id, 'IN_PROGRESS')

        # Scrape
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            content = page.content()
            browser.close()

        soup = BeautifulSoup(content, "html.parser")
        for s in soup(["script", "style"]):
            s.extract()
        text = soup.get_text(separator=' ', strip=True)

        # Chunk & Embed
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_text(text)

        vectors = []
        for i, chunk in enumerate(chunks):
            # We use the helper from rag_engine
            vector = get_embedding(chunk)
            vectors.append({
                "id": f"{job_id}#{i}",
                "values": vector,
                "metadata": {"text": chunk, "source_url": url, "job_id": job_id}
            })

        if vectors:
            index.upsert(vectors=vectors)

        update_job_status(job_id, 'COMPLETED')
        print(f"✅ Job {job_id} Completed")

    except Exception as e:
        print(f"❌ Job Failed: {e}")
        update_job_status(job_id, 'FAILED')

# --- Background Worker ---


async def start_worker_loop():
    """Runs inside the FastAPI event loop"""
    print(f"👀 Worker listening on queue: '{QUEUE_NAME}'")
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

    while True:
        try:
            # We use a non-blocking check here so we don't freeze the async loop
            # Or we run the blocking call in a separate thread
            # For simplicity in Python Async, we can use loop.run_in_executor

            # Simple polling with sleep to be async-friendly
            item = redis_client.lpop(QUEUE_NAME)

            if item:
                job_data = json.loads(item)
                # Run the blocking scraping function in a thread so it doesn't block the Chat API!
                await asyncio.to_thread(process_scraping_job, job_data)
            else:
                await asyncio.sleep(1)  # Wait a bit if queue is empty

        except Exception as e:
            print(f"⚠️ Worker Error: {e}")
            await asyncio.sleep(5)

# --- FastAPI App ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Run the worker in the background
    task = asyncio.create_task(start_worker_loop())
    yield
    # Shutdown (Optional: Cancel task)

app = FastAPI(lifespan=lifespan)


class ChatRequest(BaseModel):
    query: str


@app.post("/rag-chat")
async def chat_endpoint(req: ChatRequest):
    # 1. Search Pinecone
    results = search_pinecone(req.query)

    # 2. Extract matches
    context_chunks = results['matches']

    # 3. Generate Answer
    answer = generate_answer(req.query, context_chunks)

    return {"answer": answer, "sources": [m['metadata']['source_url'] for m in context_chunks]}
