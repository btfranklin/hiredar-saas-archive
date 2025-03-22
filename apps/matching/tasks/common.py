"""
Common utilities for matching tasks.

This module contains shared functions and utilities used by multiple task modules.
"""

import logging
import os
from typing import Any

from openai import OpenAI
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone.openapi_support.exceptions import NotFoundException, PineconeException

logger = logging.getLogger(__name__)

# Initialize clients (these should be initialized once)
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pinecone_client = Pinecone(
    api_key=os.getenv("PINECONE_API_KEY"),
    project_name=os.getenv("PINECONE_PROJECT_NAME", "Hiredar"),
)

# Initialize index reference but don't connect yet
# This allows the app to start even if the index doesn't exist
index_name = os.getenv("PINECONE_INDEX_NAME", "job-matcher")
# Get the dimension from the environment (default to 3072 for text-embedding-3-large)
DIMENSIONS = int(os.getenv("PINECONE_DIMENSIONS", "3072"))
index = None


def get_index() -> Any:
    """
    Lazily get the Pinecone index, creating a connection only when needed.
    This allows the app to start without requiring the index to exist.

    Returns:
        The Pinecone index object

    Raises:
        NotFoundException: If the index doesn't exist when this function is called
    """
    global index
    if index is None:
        try:
            index = pinecone_client.Index(index_name)
            logger.info("Connected to Pinecone index: %s", index_name)
        except NotFoundException:
            logger.warning(
                "Pinecone index '%s' not found. "
                "Please create it using 'python manage.py create_matching_index'",
                index_name,
            )
            raise
    return index


def ensure_namespaces_exist() -> None:
    """
    Ensure that required Pinecone namespaces exist.

    This function checks if the namespaces used in the application exist,
    and creates them if they don't. This helps prevent "Namespace not found" errors.
    """
    required_namespaces = ["job_openings", "talent_sheets"]

    try:
        # Get the index, which might raise an exception if it doesn't exist
        current_index = get_index()

        # Get the list of existing namespaces
        existing_namespaces = current_index.describe_index_stats()

        # Create each namespace if it doesn't exist
        # (we verify a namespace exists by checking if it appears in the stats)
        for namespace in required_namespaces:
            if namespace not in existing_namespaces.namespaces.keys():
                # To "create" a namespace, we insert a dummy vector that we'll delete immediately
                dummy_id = f"init_{namespace}"
                # Create a vector with mostly zeros but one non-zero value
                # (Pinecone requires at least one non-zero value)
                dummy_vector = [0.0] * DIMENSIONS
                dummy_vector[0] = 0.1  # Set first element to non-zero

                # Upsert the dummy vector to create the namespace
                current_index.upsert(
                    vectors=[(dummy_id, dummy_vector, {"type": "initialization"})],  # type: ignore
                    namespace=namespace,
                )
                logger.info("Created namespace '%s' in Pinecone", namespace)

                # Delete the dummy vector
                current_index.delete(ids=[dummy_id], namespace=namespace)
            else:
                logger.debug("Namespace '%s' already exists in Pinecone", namespace)

    except (NotFoundException, PineconeException) as e:
        logger.error("Error ensuring namespaces exist: %s", e)
        # Don't raise the exception - we'll let the individual operations handle errors


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
