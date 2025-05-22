"""
Cleanup tasks for job seekers.

This module contains tasks for cleaning up temporary data and records
related to job seeker processing.
"""

import logging

from django.core.cache import cache
# Schedule model was used only to *delete* periodic tasks from the Django-Q
# table.  With Celery + Beat the record lives elsewhere, so we simply ignore
# the old cleanup.  Importing the model would now fail – delete all related
# code.

from apps.resume_processing.models import ResumeProcessingTaskProgress

# Setup logging
logger = logging.getLogger(__name__)


def initialize_cleanup_once() -> None:
    """
    Disable periodic cleanup schedules and perform a one-time cleanup.

    This function removes any existing scheduled cleanup tasks and performs an immediate cleanup.
    It uses a cache lock and flag to prevent duplicate execution in the same process.
    """
    # Use a cache to prevent duplicate checks in the same process

    # Use a cache lock to prevent multiple processes from scheduling simultaneously
    cache_key = "job_seekers_cleanup_task_scheduled"
    if cache.get(cache_key):
        # Task has been checked recently by this or another process
        return

    try:
        # Always remove any existing schedules for this task so it does NOT run periodically
        # No Django-Q *Schedule* table to clean up anymore – Celery Beat uses a
        # different storage mechanism configured via settings.  If we ever add
        # a periodic cleanup job there it should be declared in
        # ``CELERY_BEAT_SCHEDULE`` instead.

        # Perform an immediate cleanup run to ensure any stale records are removed
        cleanup_resume_processing_progress()

        # Set cache flag to avoid doing this repeatedly
        cache.set(cache_key, True, 60 * 60)

    except Exception as e:
        logger.error("Error while disabling cleanup schedule: %s", e)


def cleanup_resume_processing_progress() -> None:
    """
    Clean up completed resume processing task progress records.

    This task is scheduled to run periodically to remove completed/failed
    ResumeProcessingTaskProgress records that are no longer needed.
    """
    try:
        # Clean up completed/failed records older than 5 minutes
        completed_count = ResumeProcessingTaskProgress.clean_up_completed_records(
            minutes=5
        )
        if completed_count > 0:
            logger.info(
                "Cleaned up %s completed resume processing records", completed_count
            )

        # Clean up all old records (regardless of status) older than 7 days
        old_count = ResumeProcessingTaskProgress.clean_up_old_records(days=7)
        if old_count > 0:
            logger.info("Cleaned up %s old resume processing records", old_count)

    except Exception as e:
        logger.error("Error cleaning up resume processing records: %s", e)
