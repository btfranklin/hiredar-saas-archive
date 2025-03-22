"""
Job opening embedding tasks.

This module contains tasks for embedding job openings in vector space.
"""

from typing import Any

# Use get_model to handle importing from another app without circular imports
from django.apps import apps

# Import shared utilities
from apps.matching.tasks.common import get_embedding, index, logger


def generate_enriched_text_for_job(section_name: str, raw_text: str) -> str:
    """
    Enrich raw text from a job opening using a template.
    For example: "Section: Job Description | {raw_text}"

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
    Upsert a job-related vector into the Pinecone index.

    Args:
        vector_id: Unique identifier for the vector
        embedding: The embedding vector
        metadata: Dictionary of metadata to store with the vector

    Raises:
        Exception: If the Pinecone API call fails
    """
    try:
        # Using the current Pinecone client format
        # Type ignore is needed because the pinecone-client has inconsistent type definitions
        index.upsert(
            vectors=[(vector_id, embedding, metadata)],  # type: ignore
            namespace="job_openings",  # Using namespaces for organization
        )
    except Exception as e:
        logger.error(f"Error upserting job vector {vector_id}: {e}")
        raise


def process_job_opening(job_opening_id: int) -> None:
    """
    Process a JobOpening: extract, enrich, generate embeddings, and upsert to Pinecone.

    Args:
        job_opening_id: ID of the JobOpening to process
    """
    # Get JobOpening model dynamically to avoid circular imports
    JobOpening = apps.get_model("recruiters", "JobOpening")

    try:
        job = JobOpening.objects.get(id=job_opening_id)
    except JobOpening.DoesNotExist:
        logger.error(f"JobOpening with id {job_opening_id} does not exist.")
        return

    # Skip processing if job is not active
    if not job.is_active:
        logger.info(f"Skipping embedding for inactive JobOpening {job_opening_id}")
        return

    # Define the fields to process. Adjust or add fields as needed.
    fields = {
        "Job Overview": f"{job.title}\n{job.description}",
        "Required Skills": job.required_skills,
        "Responsibilities": " ".join(
            filter(
                None,
                [job.responsibilities, job.daily_tasks, job.performance_expectations],
            )
        ),
        "Qualifications": job.required_qualifications,
        "Soft Skills": job.soft_skills,
    }

    # Process each field, ignoring empty ones
    for section, raw_text in fields.items():
        if not raw_text:
            continue

        enriched_text = generate_enriched_text_for_job(section, raw_text)
        embedding = get_embedding(enriched_text)

        # Create a unique vector ID for each section
        section_slug = section.lower().replace(" ", "_")
        vector_id = f"job_{job.id}_{section_slug}"

        # Enhanced metadata for better search filtering and result display
        metadata = {
            "job_opening_id": job.id,
            "title": job.title,
            "section": section,
            "company": job.company,
            "job_level": job.job_level,
            "employment_type": job.employment_type,
            "location": job.location,
            "salary_range": (
                f"{job.salary_min}-{job.salary_max}"
                if (job.salary_min and job.salary_max)
                else None
            ),
            "content_preview": (
                raw_text[:100] + "..." if len(raw_text) > 100 else raw_text
            ),
        }

        # Remove None values from metadata
        metadata = {k: v for k, v in metadata.items() if v is not None}

        upsert_job_embedding(vector_id, embedding, metadata)
        logger.info(
            f"Upserted embedding for JobOpening {job.id} section '{section}' (ID: {vector_id})"
        )

    logger.info(f"Completed processing embeddings for JobOpening {job.id}")


def remove_job_opening_embeddings(job_opening_id: int) -> None:
    """
    Remove all embeddings associated with a JobOpening from Pinecone.

    Args:
        job_opening_id: ID of the JobOpening to remove embeddings for

    Raises:
        Exception: If the Pinecone API call fails
    """
    try:
        # Using a filter to find all vectors for this job opening
        # Type ignore is needed because the pinecone-client has inconsistent type definitions
        filter_dict = {"job_opening_id": job_opening_id}

        index.delete(filter=filter_dict, namespace="job_openings")  # type: ignore

        logger.info(f"Deleted embeddings for JobOpening {job_opening_id}")
    except Exception as e:
        logger.error(f"Error deleting embeddings for JobOpening {job_opening_id}: {e}")
        raise
