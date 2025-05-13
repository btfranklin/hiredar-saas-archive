"""
Job opening embedding tasks.

This module contains tasks for embedding job openings in vector space.
"""

from typing import Any

# Use get_model to handle importing from another app without circular imports
from django.apps import apps

from apps.core.tasks import safe_async_task

# Import shared utilities
from apps.matching.tasks.common import DIMENSIONS, get_embedding, get_index, logger

async_task = safe_async_task


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
    Upsert a job-related vector into Pinecone.

    Args:
        vector_id: Unique identifier for the vector
        embedding: The embedding vector
        metadata: Dictionary of metadata to store with the vector

    Raises:
        Exception: If the Pinecone API call fails
    """
    try:
        # Get the Pinecone index
        index = get_index()

        # Using the current Pinecone client format
        # Type ignore is needed because the pinecone-client has inconsistent type definitions
        index.upsert(
            vectors=[(vector_id, embedding, metadata)],  # type: ignore
            namespace="job_openings",  # Using namespaces for organization
        )
    except Exception as e:
        logger.error("Error upserting job vector %s to Pinecone: %s", vector_id, e)
        raise


def create_job_opening_embeddings(job_opening_id: int, **kwargs) -> None:
    """
    Create and store embeddings for a JobOpening in Pinecone.

    Process a JobOpening by extracting key fields, generating embeddings for each section,
    and storing them in Pinecone with rich metadata.

    Args:
        job_opening_id: ID of the JobOpening to process
        **kwargs: Additional keyword arguments (ignored)
    """
    # Get JobOpening model dynamically to avoid circular imports
    JobOpening = apps.get_model("recruiters", "JobOpening")

    try:
        job = JobOpening.objects.get(id=job_opening_id)
    except JobOpening.DoesNotExist:
        logger.error("JobOpening with id %s does not exist.", job_opening_id)
        return

    # Don't process inactive jobs
    if job.status != "active":
        logger.info("Skipping inactive job %s", job.id)
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

    # Track all vector IDs we create for this job opening
    vector_ids = []

    # Process each field, ignoring empty ones
    for section, raw_text in fields.items():
        if not raw_text:
            continue

        enriched_text = generate_enriched_text_for_job(section, raw_text)
        embedding = get_embedding(enriched_text)

        # Create a unique vector ID for each section
        section_slug = section.lower().replace(" ", "_")
        vector_id = f"job_{job.id}_{section_slug}"
        vector_ids.append(vector_id)

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
            "Upserted embedding for JobOpening %s section '%s' (ID: %s)",
            job.id,
            section,
            vector_id,
        )

    logger.info("Completed processing embeddings for JobOpening %s", job.id)

    # Trigger matching task after successfully creating embeddings
    logger.info("Triggering candidate matching for JobOpening %s", job.id)
    async_task("apps.matching.tasks.create_candidate_matches", job.id)


def remove_job_opening_embeddings(job_opening_id: int) -> None:
    """
    Remove all embeddings associated with a JobOpening from Pinecone.

    Since Serverless/Starter Pinecone indexes don't support delete-by-filter operations,
    we delete by the predictable vector IDs instead.

    Args:
        job_opening_id: ID of the JobOpening to remove embeddings for
    """
    try:
        # Get the Pinecone index
        index = get_index()

        # First check if the namespace exists
        stats = index.describe_index_stats()
        if "job_openings" not in stats.namespaces.keys():
            logger.warning(
                "Namespace 'job_openings' doesn't exist yet - nothing to delete for JobOpening %s",
                job_opening_id,
            )
            return

        # Sweep delete embeddings by metadata query
        metadata_filter = {"job_opening_id": {"$eq": job_opening_id}}
        # Build a dummy vector for querying; we only care about the filter
        dummy_vector = [0.0] * DIMENSIONS
        # Query Pinecone for all matching vectors
        query_response = index.query(
            namespace="job_openings",
            vector=dummy_vector,
            top_k=100,
            filter=metadata_filter,
            include_values=False,
            include_metadata=False,
        )
        # Extract matching vector IDs
        vector_ids = [match.id for match in getattr(query_response, "matches", [])]
        # Delete all found vectors
        if vector_ids:
            index.delete(ids=vector_ids, namespace="job_openings")
        logger.info(
            "Deleted %d embeddings for JobOpening %s", len(vector_ids), job_opening_id
        )
    except Exception as e:
        # Log the error but don't raise it - we don't want to break the recruiter experience
        # if there's an issue with the embedding system
        logger.error(
            "Error deleting embeddings for JobOpening %s: %s", job_opening_id, e
        )
