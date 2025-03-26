"""
Pinecone client interactions for matching functionality.

This module contains functions for interacting with the Pinecone vector database.
"""

import logging
from typing import Any

from apps.matching.tasks.common import get_index

logger = logging.getLogger(__name__)


def query_pinecone(
    query_vector: list[float],
    namespace: str,
    top_k: int = 10,
    filter_dict: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Query Pinecone with the provided vector.

    Args:
        query_vector: The embedding vector to use as query
        namespace: The Pinecone namespace to query ('job_openings' or 'talent_sheets')
        top_k: Number of results to return
        filter_dict: Optional metadata filter to apply

    Returns:
        List of matches with metadata and scores
    """
    try:
        # Get the Pinecone index
        index = get_index()

        # Execute the query
        query_response = index.query(
            namespace=namespace,
            top_k=top_k,
            include_metadata=True,
            vector=query_vector,
            filter=filter_dict,
        )
        # The response structure depends on the Pinecone client version
        # For the gRPC client, matches are a property of the response
        return getattr(query_response, "matches", [])
    except Exception as e:
        logger.error("Error querying Pinecone: %s", e)
        return []
