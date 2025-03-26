"""
Embedding retrieval functionality.

This module contains functions for retrieving embeddings from Pinecone.
"""

import logging

from apps.matching.tasks.common import get_index

logger = logging.getLogger(__name__)


def get_talent_section_embedding(talent_id: int, section: str) -> list[float] | None:
    """
    Retrieve the embedding for a specific section of a talent sheet.

    Args:
        talent_id: ID of the talent sheet
        section: Section name (e.g., 'Promotional Blurb', 'Skill Overview')

    Returns:
        The embedding vector or None if not found
    """
    try:
        # Get the Pinecone index
        index = get_index()

        # Convert section name to slug format (lowercase with underscores)
        section_slug = section.lower().replace(" ", "_")
        vector_id = f"talent_{talent_id}_{section_slug}"
        result = index.fetch(ids=[vector_id], namespace="talent_sheets")

        if not result.vectors:
            logger.warning(
                "Vector %s not found in Pinecone namespace 'talent_sheets'.", vector_id
            )
            return None

        return result.vectors[vector_id].values
    except Exception as e:
        logger.error("Error fetching talent embedding: %s", e)
        return None


def get_job_section_embedding(job_id: int, section: str) -> list[float] | None:
    """
    Retrieve the embedding for a specific section of a job opening.

    Args:
        job_id: ID of the job opening
        section: Section name (e.g., 'Job Overview', 'Required Skills')

    Returns:
        The embedding vector or None if not found
    """
    try:
        # Get the Pinecone index
        index = get_index()

        # Convert section name to slug format (lowercase with underscores)
        section_slug = section.lower().replace(" ", "_")
        vector_id = f"job_{job_id}_{section_slug}"
        result = index.fetch(ids=[vector_id], namespace="job_openings")

        if not result.vectors:
            logger.warning(
                "Vector %s not found in Pinecone namespace 'job_openings'.", vector_id
            )
            return None

        return result.vectors[vector_id].values
    except Exception as e:
        logger.error("Error fetching job embedding: %s", e)
        return None
