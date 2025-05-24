"""
Task for creating embeddings for a JobOpening in Pinecone.
"""

from typing import Any

from celery import shared_task
from django.apps import apps

from apps.matching.services.job_opening_embeddings import (
    generate_enriched_text_for_job,
    upsert_job_embedding,
)
from apps.matching.tasks.common import get_embedding, logger


@shared_task(name="apps.matching.tasks.create_job_opening_embeddings")
def create_job_opening_embeddings(job_opening_id: int, **kwargs) -> dict[str, Any]:
    """
    Create and store embeddings for a JobOpening in Pinecone.

    Process a JobOpening by extracting key fields, generating embeddings for each section,
    and storing them in Pinecone with rich metadata.

    Args:
        job_opening_id: ID of the JobOpening to process
        **kwargs: Additional keyword arguments (ignored)

    Returns:
        dict: Result containing status and job_opening_id
    """
    JobOpening = apps.get_model("recruiters", "JobOpening")

    try:
        job = JobOpening.objects.get(id=job_opening_id)
    except JobOpening.DoesNotExist:
        logger.error("JobOpening with id %s does not exist.", job_opening_id)
        return {
            "status": "error",
            "message": f"JobOpening with id {job_opening_id} does not exist",
        }

    if job.status != "active":
        logger.info("Skipping inactive job %s", job.id)
        return {"status": "skipped", "message": f"Job {job.id} is not active"}

    fields: dict[str, str] = {
        "Job Overview": f"{job.title}\n{job.description}",
        "Required Skills": " ".join(
            filter(None, [job.required_skills, job.soft_skills])
        ),
        "Responsibilities": " ".join(
            filter(
                None,
                [job.responsibilities, job.daily_tasks, job.performance_expectations],
            )
        ),
        "Qualifications": job.required_qualifications,
    }

    vector_ids: list[str] = []

    for section, raw_text in fields.items():
        if not raw_text:
            continue

        enriched_text = generate_enriched_text_for_job(section, raw_text)
        embedding = get_embedding(enriched_text)

        section_slug = section.lower().replace(" ", "_")
        vector_id = f"job_{job.id}_{section_slug}"
        vector_ids.append(vector_id)

        metadata: dict[str, Any] = {
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
        metadata = {k: v for k, v in metadata.items() if v is not None}

        upsert_job_embedding(vector_id, embedding, metadata)
        logger.info(
            "Upserted embedding for JobOpening %s section '%s' (ID: %s)",
            job.id,
            section,
            vector_id,
        )

    logger.info("Completed processing embeddings for JobOpening %s", job.id)

    # Return the job_opening_id for the next task in the chain
    return {"status": "success", "job_opening_id": job.id}
