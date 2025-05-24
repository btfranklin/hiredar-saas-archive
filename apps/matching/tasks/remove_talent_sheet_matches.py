"""
Task for removing matches for a TalentSheet.
"""

from celery import shared_task
from django.db import transaction

from apps.matching.models import CandidateMatch
from apps.matching.tasks.common import logger

@shared_task(name="apps.matching.tasks.remove_talent_sheet_matches")
def remove_talent_sheet_matches(talent_id: int, **kwargs) -> None:
    """
    Remove all matches for a talent sheet.

    Args:
        talent_id: ID of the talent sheet to process
        **kwargs: Additional arguments (ignored)
    """
    try:
        with transaction.atomic():
            CandidateMatch.objects.filter(talent_sheet_id=talent_id).delete()
        logger.info("Removed matches for talent sheet %s", talent_id)
    except Exception as e:
        logger.error("Error removing matches for talent sheet %s: %s", talent_id, e)
        raise