"""
Cleanup tasks for job seekers.

This module contains tasks for cleaning up temporary data and records
related to job seeker processing.
"""

import logging

from django.core.cache import cache
from django_q.models import Schedule
from django_q.tasks import schedule

from apps.resume_processing.models import ResumeProcessingTaskProgress

# Setup logging
logger = logging.getLogger(__name__)


def ensure_cleanup_scheduled() -> None:
    """
    Ensure the cleanup task is scheduled.

    This function checks if the cleanup task is already scheduled and if not,
    schedules it. It's designed to be called lazily after the app is fully loaded.
    """
    # Use a cache to prevent duplicate checks in the same process

    # Use a cache lock to prevent multiple processes from scheduling simultaneously
    cache_key = "job_seekers_cleanup_task_scheduled"
    if cache.get(cache_key):
        # Task has been checked recently by this or another process
        return

    try:
        # Check if valid schedules already exist
        existing_schedules = Schedule.objects.filter(
            name="cleanup_resume_processing_progress",
            func="apps.resume_processing.tasks.cleanup_tasks.cleanup_resume_processing_progress",
            minutes=15,
        )

        # Clean up any duplicate or invalid schedules
        invalid_schedules = Schedule.objects.filter(
            name="cleanup_resume_processing_progress"
        ).exclude(
            func="apps.resume_processing.tasks.cleanup_tasks.cleanup_resume_processing_progress",
            minutes=15,
        )

        if invalid_schedules.exists():
            logger.warning(
                "Found %s invalid cleanup schedules - deleting",
                invalid_schedules.count(),
            )
            invalid_schedules.delete()

        # If we have multiple valid schedules, keep only the oldest one
        if existing_schedules.count() > 1:
            logger.warning(
                "Found %s duplicate cleanup schedules - keeping only the oldest",
                existing_schedules.count(),
            )
            # Keep the oldest schedule (assuming it has the lowest ID)
            oldest = existing_schedules.order_by("pk").first()
            if oldest:
                existing_schedules.exclude(pk=oldest.pk).delete()
                existing = oldest
            else:
                # Somehow we had multiple schedules but couldn't get the first one
                # Delete all and create a new one
                existing_schedules.delete()
                existing = None
        else:
            existing = existing_schedules.first()

        # Create schedule if it doesn't exist
        if not existing:
            schedule(
                "apps.resume_processing.tasks.cleanup_tasks.cleanup_resume_processing_progress",
                name="cleanup_resume_processing_progress",
                schedule_type=Schedule.MINUTES,
                minutes=15,
            )
            logger.info(
                "Scheduled task cleanup_resume_processing_progress to run every 15 minutes"
            )

        # Set a cache flag to prevent repeated checks for 60 minutes
        # This is much longer than before to reduce DB access
        cache.set(cache_key, True, 60 * 60)

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
