"""
Task for removing matches for a JobOpening.
"""

from celery import shared_task
from django.db import transaction

from apps.matching.models import CandidateMatch
from apps.matching.tasks.common import logger

@shared_task(name="apps.matching.tasks.remove_job_opening_matches")
def remove_job_opening_matches(job_id: int, **kwargs) -> None:
    """
    Remove all matches for a job opening.

    Args:
        job_id: ID of the job opening to process
        **kwargs: Additional arguments (ignored)
    """
    try:
        with transaction.atomic():
            CandidateMatch.objects.filter(job_opening_id=job_id).delete()
        logger.info("Removed matches for job opening %s", job_id)
    except Exception as e:
        logger.error("Error removing matches for job opening %s: %s", job_id, e)
        raise