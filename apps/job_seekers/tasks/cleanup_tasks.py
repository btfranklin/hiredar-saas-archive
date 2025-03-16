"""
Cleanup tasks for job seekers.

This module contains tasks for cleaning up temporary data and records
related to job seeker processing.
"""

import logging

from django_q.models import Schedule
from django_q.tasks import schedule

from apps.job_seekers.models import ResumeProcessingTaskProgress

# Setup logging
logger = logging.getLogger(__name__)


def ensure_cleanup_scheduled() -> None:
    """
    Ensure the cleanup task is scheduled.

    This function checks if the cleanup task is already scheduled and if not,
    schedules it. It's designed to be called lazily after the app is fully loaded.
    """
    try:
        # Check if schedule already exists
        existing = Schedule.objects.filter(
            name="cleanup_resume_processing_progress"
        ).first()

        if existing:
            # If task exists but is not set to repeat every 15 minutes, update it
            if (
                existing.minutes != 15
                or existing.func
                != "apps.job_seekers.tasks.cleanup_tasks.cleanup_resume_processing_progress"
            ):
                existing.delete()
                existing = None

        # Create schedule if it doesn't exist
        if not existing:
            schedule(
                "apps.job_seekers.tasks.cleanup_tasks.cleanup_resume_processing_progress",
                name="cleanup_resume_processing_progress",
                schedule_type=Schedule.MINUTES,
                minutes=15,
            )
            logger.info(
                "Scheduled task cleanup_resume_processing_progress to run every 15 minutes"
            )
    except Exception as e:
        logger.error("Failed to schedule cleanup task: %s", e)


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
