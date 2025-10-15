"""
Common utilities for matching tasks.

This module contains shared functions and utilities used by multiple task modules.
"""

import logging
import os
from functools import lru_cache
from typing import Any

from django.conf import settings  # Import Django settings
from pinecone import Pinecone
from pinecone.openapi_support.exceptions import NotFoundException, PineconeException

from hiredar.llm import embed, get_client

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Lazy client factories
# -----------------------------------------------------------------------------


def get_openai_client():  # kept for backward compatibility within this module
    """Return the shared OpenAI client instance (or *None* if unavailable)."""

    try:
        return get_client()
    except RuntimeError as exc:
        logger.warning("OpenAI unavailable: %s", exc)
        return None


@lru_cache(maxsize=1)
def get_pinecone_client() -> Pinecone | None:
    """Return a singleton Pinecone client or *None* if the API key is absent."""
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        logger.warning(
            "PINECONE_API_KEY is not set; Pinecone features are disabled during this run"
        )
        return None

    return Pinecone(api_key=api_key, project_name=settings.PINECONE_PROJECT_NAME)


# Configuration from Django settings
index_name = settings.PINECONE_INDEX_NAME
index_host = settings.PINECONE_INDEX_HOST
DIMENSIONS = settings.PINECONE_DIMENSIONS


def get_index() -> Any:
    """
    Get the Pinecone index efficiently.

    In production, uses the index host URL directly to eliminate a round trip
    to the Pinecone control plane. In development, falls back to using the index name.

    Returns:
        The Pinecone index object

    Raises:
        NotFoundException: If the index doesn't exist when this function is called
    """
    try:
        client = get_pinecone_client()
        if client is None:
            raise RuntimeError("Pinecone client unavailable; missing API key")

        if index_host:
            return client.Index(host=index_host)

        return client.Index(index_name)
    except NotFoundException:
        logger.warning(
            "Pinecone index '%s' not found. "
            "Please create it using 'python manage.py create_matching_index'",
            index_name,
        )
        raise


def get_index_host() -> str:
    """
    Get the host URL for the index.

    This is useful for setting up the PINECONE_INDEX_HOST environment variable
    in production environments.

    Returns:
        The host URL for the index

    Raises:
        Exception: If the index doesn't exist or can't be described
    """
    # Use the REST client for admin operations
    admin_client = get_pinecone_client()
    if admin_client is None:
        raise RuntimeError("Pinecone client unavailable; missing API key")

    host = admin_client.describe_index(index_name).host
    logger.info("Pinecone index '%s' host URL: %s", index_name, host)
    return host


def ensure_namespaces_exist() -> None:
    """
    Ensure that required Pinecone namespaces exist.

    This function checks if the namespaces used in the application exist,
    and creates them if they don't. This helps prevent "Namespace not found" errors.
    """
    required_namespaces = ["job_openings", "candidate_profiles"]

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
        client = get_openai_client()
        if client is None:
            raise RuntimeError("OpenAI client unavailable; missing API key")

        return embed([text], model=settings.MATCHING_EMBEDDING_MODEL)[0]
    except Exception as e:
        logger.error("Embedding API error for text: %s... Error: %s", text[:50], e)
        raise
