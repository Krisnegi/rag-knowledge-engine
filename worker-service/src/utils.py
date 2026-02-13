import os
from dotenv import load_dotenv

# LangChain imports
from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore

load_dotenv()


def get_embeddings(task_type: str):
    """Generates a 768-dim vector for a query or document."""

    return GoogleGenerativeAIEmbeddings(
        model=os.getenv("EMBEDDING_MODEL"),
        google_api_key=os.getenv("GEMINI_API_KEY"),
        task_type=task_type
    )


def get_llm():
    """Returns the LangChain wrapper for Groq"""
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )


def get_retriever(user_id: str):
    """
    Returns a Pinecone Retriever specific to a User ID.
    """
    # 1. Initialize Embeddings (Same model as your ingestion)
    embeddings = get_embeddings("retrieval_query")

    # 2. Connect to Pinecone Index via LangChain
    vectorstore = PineconeVectorStore(
        index_name=os.getenv("PINECONE_INDEX_NAME"),
        embedding=embeddings,
        pinecone_api_key=os.getenv("PINECONE_API_KEY")
    )

    # 3. Return as a Retriever with the Metadata Filter
    return vectorstore.as_retriever(
        search_kwargs={
            "k": 3,
            "filter": {"user_id": {"$eq": user_id}}  # Strict user isolation
        }
    )
