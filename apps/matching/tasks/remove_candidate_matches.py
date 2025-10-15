"""
Task for removing matches for a CandidateProfile.
"""

from celery import shared_task
from django.db import transaction

from apps.matching.models import CandidateMatch
from apps.matching.tasks.common import logger


@shared_task(name="apps.matching.tasks.remove_candidate_matches")
def remove_candidate_matches(candidate_profile_id: int, **kwargs) -> None:
    """
    Remove all matches for a candidate profile.
    """
    try:
        with transaction.atomic():
            CandidateMatch.objects.filter(
                candidate_profile_id=candidate_profile_id
            ).delete()
        logger.info("Removed matches for candidate profile %s", candidate_profile_id)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error(
            "Error removing matches for candidate profile %s: %s",
            candidate_profile_id,
            exc,
        )
        raise
