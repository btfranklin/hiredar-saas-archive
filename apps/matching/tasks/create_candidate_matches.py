"""
Task for creating candidate matches for a job opening.
"""

from collections import defaultdict
from typing import Any

from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.db import transaction

from apps.core.utils.task_utils import IdempotentTaskManager
from apps.matching.core.matching import match_job_to_talents
from apps.matching.core.retrieval import get_job_section_embedding
from apps.matching.services.candidate_match_service import CandidateMatchService
from apps.matching.tasks.common import logger
from apps.matching.tasks.create_job_opening_embeddings import (
    create_job_opening_embeddings,
)


@shared_task(
    name="apps.matching.tasks.create_candidate_matches",
    bind=True,
)
def create_candidate_matches(
    self, result: dict[str, Any] | int | None = None, **kwargs
) -> dict[str, Any]:
    """
    Create candidate matches for a job opening.

    Args:
        result: Either a dict with job_opening_id from previous task, or the job_id directly
        **kwargs: Additional arguments (ignored)

    Returns:
        dict: Result containing status and job_opening_id
    """
    # Handle different input types
    if isinstance(result, dict):
        raw_job_id = result.get("job_opening_id")
        if raw_job_id is None:
            logger.error("No job_opening_id found in result dict: %s", result)
            return {"status": "error", "message": "No job_opening_id in result"}
    elif isinstance(result, int):
        raw_job_id = result
    else:
        logger.error(
            "Invalid input type for create_candidate_matches: %s", type(result)
        )
        return {"status": "error", "message": f"Invalid input type: {type(result)}"}

    try:
        job_id = int(raw_job_id)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        try:
            job_id = int(float(raw_job_id))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            logger.error("Unable to coerce job_opening_id=%s to int", raw_job_id)
            return {
                "status": "error",
                "message": f"Invalid job_opening_id: {raw_job_id}",
            }

    try:
        # Clean up the running marker when task completes
        def cleanup_task_marker():
            if hasattr(self, "request") and self.request.id:
                IdempotentTaskManager.unmark_task_running(self.request.id)

        JobOpening = apps.get_model("recruiters", "JobOpening")
        job = JobOpening.objects.get(id=job_id)

        if job.status != "active":
            logger.warning("Job opening %s is not active, skipping matching", job_id)
            return {"status": "skipped", "message": f"Job {job_id} is not active"}

        sections_to_check = [
            "Job Overview",
            "Required Skills",
            "Responsibilities",
            "Qualifications",
        ]

        # Determine if the job currently has *any* embeddings stored in Pinecone.
        has_any_embeddings = any(
            get_job_section_embedding(job_id, section) is not None
            for section in sections_to_check
        )

        if not has_any_embeddings:
            logger.warning(
                "No embeddings found for job %s; creating embeddings before matching.",
                job_id,
            )

            try:
                create_job_opening_embeddings(
                    job_id
                )  # Run synchronously within the worker
            except Exception as embed_exc:
                logger.error(
                    "Failed to create embeddings for job %s during match creation: %s",
                    job_id,
                    embed_exc,
                )
                # Proceed; matching will produce empty results

        # Run matching after ensuring embeddings exist (or re-attempted to create)
        match_results = match_job_to_talents(job_id, top_k=20)

        with transaction.atomic():
            match_type_mapping = {
                "holistic_matches": "holistic",
                "skills_matches": "skills",
                "experience_matches": "experience",
                "wildcard_matches": "wildcard",
                "qualifications_matches": "qualifications",
            }

            all_matches_by_talent: dict[int, dict[str, float]] = defaultdict(dict)

            for result_key, match_type in match_type_mapping.items():
                matches = match_results.get(result_key, [])

                for match in matches:
                    raw_talent_sheet_id = match["metadata"].get("talent_sheet_id")
                    try:
                        talent_sheet_id = int(raw_talent_sheet_id)  # type: ignore[arg-type]
                    except (TypeError, ValueError):
                        try:
                            talent_sheet_id = int(float(raw_talent_sheet_id))  # type: ignore[arg-type]
                        except (TypeError, ValueError):
                            logger.warning(
                                "Skipping match with invalid talent_sheet_id=%s",
                                raw_talent_sheet_id,
                            )
                            continue

                    score = match["score"]

                    all_matches_by_talent[talent_sheet_id][match_type] = score

            TalentSheet = apps.get_model("job_seekers", "TalentSheet")
            valid_talent_ids = set(
                TalentSheet.objects.filter(
                    id__in=all_matches_by_talent.keys()
                ).values_list("id", flat=True)
            )

            min_match_score = getattr(settings, "MATCHING_MIN_SCORE", 0.5)

            for talent_sheet_id, talent_scores in all_matches_by_talent.items():
                if talent_sheet_id not in valid_talent_ids:
                    logger.warning(
                        "Skipping match creation for missing TalentSheet %s",
                        talent_sheet_id,
                    )
                    continue

                if max(talent_scores.values(), default=0) < min_match_score:
                    continue

                try:
                    CandidateMatchService.safe_upsert_candidate_match(
                        job_opening_id=job.id,
                        talent_sheet_id=talent_sheet_id,
                        score_updates=talent_scores,
                        is_analyzed=False,
                    )

                except Exception as e:
                    logger.error(
                        "Error creating consolidated match for talent sheet %s: %s",
                        talent_sheet_id,
                        e,
                    )

        logger.info("Created/updated matches for job opening %s", job_id)
        cleanup_task_marker()
        return {
            "status": "success",
            "job_opening_id": job_id,
            "matches_created": len(all_matches_by_talent),
        }
    except Exception as e:
        logger.error("Error creating matches for job opening %s: %s", job_id, e)
        cleanup_task_marker()
        raise
