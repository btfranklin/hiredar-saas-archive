"""
Common utilities for matching tasks.

This module contains shared functions and utilities used by multiple task modules.
"""

import logging
import os

from openai import OpenAI
from pinecone.grpc import PineconeGRPC as Pinecone

logger = logging.getLogger(__name__)

# Initialize clients (these should be initialized once)
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pinecone_client = Pinecone(
    api_key=os.getenv("PINECONE_API_KEY"),
    project_name=os.getenv("PINECONE_PROJECT_NAME", "Hiredar"),
)
index = pinecone_client.Index(os.getenv("PINECONE_INDEX_NAME", "job-matcher"))


def get_embedding(text: str) -> list[float]:
    """
    Generate an embedding vector using OpenAI's embedding API.

    Args:
        text: The text to embed

    Returns:
        List of floating point values representing the embedding vector

    Raises:
        Exception: If the OpenAI API call fails
    """
    try:
        # Using the current OpenAI client API
        response = openai_client.embeddings.create(
            input=text,
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"),
        )
        # Extract the embedding from the response
        return response.data[0].embedding
    except Exception as e:
        logger.error("Embedding API error for text: %s... Error: %s", text[:50], e)
        raise
