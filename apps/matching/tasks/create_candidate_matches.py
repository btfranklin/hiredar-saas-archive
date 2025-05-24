"""
Task for creating candidate matches for a job opening.
"""

from celery import shared_task
from django.apps import apps
from django.db import transaction

from apps.matching.core.matching import match_job_to_talents
from apps.matching.models import CandidateMatch
from apps.matching.tasks.common import logger

@shared_task(name="apps.matching.tasks.create_candidate_matches")
def create_candidate_matches(job_id: int, **kwargs) -> None:
    """
    Create candidate matches for a job opening.

    Args:
        job_id: ID of the job opening to process
        **kwargs: Additional arguments (ignored)
    """
    try:
        JobOpening = apps.get_model("recruiters", "JobOpening")
        job = JobOpening.objects.get(id=job_id)

        if job.status != "active":
            logger.warning("Job opening %s is not active, skipping matching", job_id)
            return

        match_results = match_job_to_talents(job_id, top_k=20)

        with transaction.atomic():
            match_type_mapping = {
                "holistic_matches": "holistic",
                "skills_matches": "skills",
                "experience_matches": "experience",
                "wildcard_matches": "wildcard",
                "qualifications_matches": "qualifications",
            }

            all_matches_by_talent: dict[int, dict[str, float]] = {}

            for result_key, match_type in match_type_mapping.items():
                matches = match_results.get(result_key, [])

                for match in matches:
                    talent_sheet_id = match["metadata"]["talent_sheet_id"]
                    score = match["score"]

                    if talent_sheet_id not in all_matches_by_talent:
                        all_matches_by_talent[talent_sheet_id] = {}

                    all_matches_by_talent[talent_sheet_id][match_type] = score

            TalentSheet = apps.get_model("job_seekers", "TalentSheet")

            for talent_sheet_id, talent_scores in all_matches_by_talent.items():
                if all(score < 0.5 for score in talent_scores.values()):
                    continue

                try:
                    talent_sheet = TalentSheet.objects.get(id=talent_sheet_id)

                    CandidateMatch.objects.update_or_create(
                        job_opening=job,
                        talent_sheet=talent_sheet,
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
                        "Error creating consolidated match for talent sheet %s: %s",
                        talent_sheet_id,
                        e,
                    )

        logger.info("Created/updated matches for job opening %s", job_id)
    except Exception as e:
        logger.error("Error creating matches for job opening %s: %s", job_id, e)
        raise