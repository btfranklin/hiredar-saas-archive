"""
Service functions for job opening embeddings.
"""

from typing import Any

from apps.matching.tasks.common import get_index, logger

def generate_enriched_text_for_job(section_name: str, raw_text: str) -> str:
    """
    Enrich raw text from a job opening using a template.
    For example: "Section: Job Overview | {raw_text}"

    Args:
        section_name: Name of the section (e.g., "Job Overview", "Required Skills")
        raw_text: The raw text content to enrich

    Returns:
        Formatted text with section context
    """
    return f"Section: {section_name} | {raw_text.strip()}"

def upsert_job_embedding(
    vector_id: str, embedding: list[float], metadata: dict[str, Any]
) -> None:
    """
    Upsert a job-related vector into Pinecone.

    Args:
        vector_id: Unique identifier for the vector
        embedding: The embedding vector
        metadata: Dictionary of metadata to store with the vector

    Raises:
        Exception: If the Pinecone API call fails
    """
    try:
        index = get_index()

        index.upsert(
            vectors=[(vector_id, embedding, metadata)],  # type: ignore
            namespace="job_openings",
        )
    except Exception as e:
        logger.error("Error upserting job vector %s to Pinecone: %s", vector_id, e)
        raise