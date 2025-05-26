"""
Task for matching a TalentSheet against all active job openings.
"""

from typing import Any

from celery import shared_task
from django.apps import apps
from django.db import transaction

from apps.matching.core.matching import match_job_to_talents
from apps.matching.services.candidate_match_service import CandidateMatchService
from apps.matching.tasks.common import logger


@shared_task(name="apps.matching.tasks.match_talent_to_active_jobs")
def match_talent_to_active_jobs(
    result: dict[str, Any] | int | None = None, **kwargs
) -> dict[str, Any]:
    """
    Match a talent sheet against all active job openings.

    Args:
        result: Either a dict with talent_sheet_id from previous task, or the talent_id directly
        **kwargs: Additional arguments (ignored)

    Returns:
        dict: Result containing status and talent_sheet_id
    """
    # Handle different input types
    if isinstance(result, dict):
        talent_id = result.get("talent_sheet_id")
        if not talent_id:
            logger.error("No talent_sheet_id found in result dict: %s", result)
            return {"status": "error", "message": "No talent_sheet_id in result"}
    elif isinstance(result, int):
        talent_id = result
    else:
        logger.error(
            "Invalid input type for match_talent_to_active_jobs: %s", type(result)
        )
        return {"status": "error", "message": f"Invalid input type: {type(result)}"}

    try:
        JobOpening = apps.get_model("recruiters", "JobOpening")
        TalentSheet = apps.get_model("job_seekers", "TalentSheet")

        try:
            talent = TalentSheet.objects.get(id=talent_id)
        except TalentSheet.DoesNotExist:
            logger.warning(
                "Talent sheet %s not found, skipping matching to active jobs",
                talent_id,
            )
            return {"status": "error", "message": f"Talent sheet {talent_id} not found"}

        if not talent.is_published:
            logger.warning(
                "Talent sheet %s is not published, skipping matching", talent_id
            )
            return {
                "status": "skipped",
                "message": f"Talent sheet {talent_id} is not published",
            }

        active_jobs = JobOpening.objects.filter(status="active")
        matches_created = 0

        for job in active_jobs:
            try:
                match_results = match_job_to_talents(job.id, top_k=20)

                with transaction.atomic():
                    match_type_mapping = {
                        "holistic_matches": "holistic",
                        "skills_matches": "skills",
                        "experience_matches": "experience",
                        "wildcard_matches": "wildcard",
                        "qualifications_matches": "qualifications",
                    }

                    talent_scores: dict[str, float] = {}

                    for result_key, match_type in match_type_mapping.items():
                        matches = match_results.get(result_key, [])

                        for match in matches:
                            if str(match["metadata"]["talent_sheet_id"]) != str(
                                talent_id
                            ):
                                continue

                            score = match["score"]
                            talent_scores[match_type] = score

                    if all(score < 0.5 for score in talent_scores.values()):
                        continue

                    try:
                        CandidateMatchService.safe_upsert_candidate_match(
                            job_opening_id=job.id,
                            talent_sheet_id=talent.id,
                            score_updates=talent_scores,
                            is_analyzed=False,
                        )
                        matches_created += 1

                    except Exception as e:
                        logger.error(
                            "Error creating consolidated match for job opening %s: %s",
                            job.id,
                            e,
                        )

            except Exception as e:
                logger.error("Error processing job opening %s: %s", job.id, e)

        logger.info("Created/updated matches for talent sheet %s", talent_id)
        return {
            "status": "success",
            "talent_sheet_id": talent_id,
            "matches_created": matches_created,
        }
    except Exception as e:
        logger.error("Error creating matches for talent sheet %s: %s", talent_id, e)
        raise
