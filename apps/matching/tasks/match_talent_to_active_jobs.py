"""
Task for matching a TalentSheet against all active job openings.
"""

from celery import shared_task
from django.apps import apps
from django.db import transaction

from apps.matching.core.matching import match_job_to_talents
from apps.matching.models import CandidateMatch
from apps.matching.tasks.common import logger

@shared_task(name="apps.matching.tasks.match_talent_to_active_jobs")
def match_talent_to_active_jobs(talent_id: int, **kwargs) -> None:
    """
    Match a talent sheet against all active job openings.

    Args:
        talent_id: ID of the talent sheet to process
        **kwargs: Additional arguments (ignored)
    """
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
            return

        if not talent.is_published:
            logger.warning(
                "Talent sheet %s is not published, skipping matching", talent_id
            )
            return

        active_jobs = JobOpening.objects.filter(status="active")

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
                        CandidateMatch.objects.update_or_create(
                            job_opening=job,
                            talent_sheet=talent,
                            defaults={
                                "holistic_score": talent_scores.get("holistic", 0),
                                "skills_score": talent_scores.get("skills", 0),
                                "experience_score": talent_scores.get("experience", 0),
                                "wildcard_score": talent_scores.get("wildcard", 0),
                                "qualifications_score": talent_scores.get(
                                    "qualifications", 0
                                ),
                                "is_analyzed": False,
                            },
                        )

                    except Exception as e:
                        logger.error(
                            "Error creating consolidated match for job opening %s: %s",
                            job.id,
                            e,
                        )

            except Exception as e:
                logger.error("Error processing job opening %s: %s", job.id, e)

        logger.info("Created/updated matches for talent sheet %s", talent_id)
    except Exception as e:
        logger.error("Error creating matches for talent sheet %s: %s", talent_id, e)
        raise