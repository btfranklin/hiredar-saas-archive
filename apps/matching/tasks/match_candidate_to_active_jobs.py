"""
Task for matching a CandidateProfile against all active job openings.
"""

from typing import Any

from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.db import transaction

from apps.matching.core.matching import match_job_to_candidates
from apps.matching.services.candidate_match_service import CandidateMatchService
from apps.matching.tasks.common import logger


@shared_task(name="apps.matching.tasks.match_candidate_to_active_jobs")
def match_candidate_to_active_jobs(
    result: dict[str, Any] | int | None = None, **kwargs
) -> dict[str, Any]:
    """
    Match a candidate profile against all active job openings.

    Args:
        result: Either a dict with candidate_profile_id from previous task, or the candidate_id directly
        **kwargs: Additional arguments (ignored)

    Returns:
        dict: Result containing status and candidate_profile_id
    """
    # Handle different input types
    if isinstance(result, dict):
        raw_candidate_id = result.get("candidate_profile_id")
        if raw_candidate_id is None:
            logger.error("No candidate_profile_id found in result dict: %s", result)
            return {"status": "error", "message": "No candidate_profile_id in result"}
    elif isinstance(result, int):
        raw_candidate_id = result
    else:
        logger.error(
            "Invalid input type for match_candidate_to_active_jobs: %s", type(result)
        )
        return {"status": "error", "message": f"Invalid input type: {type(result)}"}

    try:
        candidate_id = int(raw_candidate_id)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        try:
            candidate_id = int(float(raw_candidate_id))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            logger.error(
                "Unable to coerce candidate_profile_id=%s to int", raw_candidate_id
            )
            return {
                "status": "error",
                "message": f"Invalid candidate_profile_id: {raw_candidate_id}",
            }

    try:
        JobOpening = apps.get_model("recruiters", "JobOpening")
        CandidateProfile = apps.get_model("candidates", "CandidateProfile")

        try:
            candidate = CandidateProfile.objects.get(id=candidate_id)
        except CandidateProfile.DoesNotExist:
            logger.warning(
                "Candidate profile %s not found, skipping matching to active jobs",
                candidate_id,
            )
            return {
                "status": "error",
                "message": f"Candidate profile {candidate_id} not found",
            }

        if not candidate.is_published:
            logger.warning(
                "Candidate profile %s is not published, skipping matching",
                candidate_id,
            )
            return {
                "status": "skipped",
                "message": f"Candidate profile {candidate_id} is not published",
            }

        active_jobs = JobOpening.objects.filter(status="active")
        matches_created = 0

        for job in active_jobs:
            try:
                match_results = match_job_to_candidates(job.id, top_k=20)

                with transaction.atomic():
                    match_type_mapping = {
                        "holistic_matches": "holistic",
                        "skills_matches": "skills",
                        "experience_matches": "experience",
                        "wildcard_matches": "wildcard",
                        "qualifications_matches": "qualifications",
                    }

                    candidate_scores: dict[str, float] = {}

                    for result_key, match_type in match_type_mapping.items():
                        matches = match_results.get(result_key, [])

                        for match in matches:
                            raw_match_candidate_id = match["metadata"].get(
                                "candidate_profile_id"
                            )
                            try:
                                match_candidate_id = int(raw_match_candidate_id)  # type: ignore[arg-type]
                            except (TypeError, ValueError):
                                try:
                                    match_candidate_id = int(
                                        float(raw_match_candidate_id)
                                    )  # type: ignore[arg-type]
                                except (TypeError, ValueError):
                                    logger.warning(
                                        "Skipping match with invalid candidate_profile_id=%s",
                                        raw_match_candidate_id,
                                    )
                                    continue

                            if match_candidate_id != candidate_id:
                                continue

                            score = match["score"]
                            candidate_scores[match_type] = score

                    min_match_score = getattr(settings, "MATCHING_MIN_SCORE", 0.5)
                    if max(candidate_scores.values(), default=0) < min_match_score:
                        continue

                    try:
                        CandidateMatchService.safe_upsert_candidate_match(
                            job_opening_id=job.id,
                            candidate_profile_id=candidate.id,
                            score_updates=candidate_scores,
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

        logger.info("Created/updated matches for candidate profile %s", candidate_id)
        return {
            "status": "success",
            "candidate_profile_id": candidate_id,
            "matches_created": matches_created,
        }
    except Exception as e:
        logger.error(
            "Error creating matches for candidate profile %s: %s", candidate_id, e
        )
        raise
