import os
from google import genai
from google.genai import types
from pinecone import Pinecone
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Clients
google_client = genai.Client(api_key=GEMINI_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)
groq_client = Groq(api_key=GROQ_API_KEY)


def get_embedding(text: str, task_type="RETRIEVAL_DOCUMENT"):
    """Generates a 768-dim vector for a query or document."""
    result = google_client.models.embed_content(
        model="text-embedding-004",
        contents=text,
        config=types.EmbedContentConfig(task_type=task_type)
    )
    return result.embeddings[0].values


def search_pinecone(query: str, user_id: str, top_k: int = 3):
    """
    1. Embeds the user's question.
    2. Searches Pinecone for the 3 most similar text chunks.
    """
    # Important: For queries, we might technically use task_type="RETRIEVAL_QUERY"
    # But usually, keeping it consistent works fine for simple RAG.
    query_vector = get_embedding(query, task_type="RETRIEVAL_QUERY")

    # Tell Pinecone: "Only search vectors where metadata.user_id == user_id"
    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,  # We need the actual text back!
        filter={
            "user_id": {"$eq": user_id}  # <--- THE MAGIC FILTER
        }
    )

    return results


def generate_answer(query: str, context_chunks: list):
    """Generates an answer using Meta Llama 3 via Groq"""
    # 1. Combine all the chunks into one big string
    context_text = "\n\n".join([chunk['metadata']['text']
                               for chunk in context_chunks])

    # 2. Build the Strict Prompt
    prompt = f"""
    You are a helpful AI assistant. Use the following context to answer the user's question.
    If the answer is NOT in the context, say "I don't know based on the provided documents."
    
    --- CONTEXT ---
    {context_text}
    ---------------
    
    User Question: {query}
    """

    # 3. Call Llama 3
    chat_completion = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.1-8b-instant",
        temperature=0.3,
    )

    return chat_completion.choices[0].message.content
