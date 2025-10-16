"""
Cleanup tasks for resume processing.

This module contains Celery tasks for cleaning up temporary data and records
related to resume processing.
"""

import logging

from celery import shared_task

from apps.candidates.models import ResumeProcessingTaskProgress

# Setup logging
logger = logging.getLogger(__name__)


@shared_task(
    name="apps.candidates.tasks.resume_processing.cleanup.cleanup_resume_processing_progress"
)
def cleanup_resume_processing_progress() -> dict[str, str | int]:
    """
    Clean up completed resume processing task progress records.

    This task is scheduled to run periodically via Celery Beat to remove completed/failed
    ResumeProcessingTaskProgress records that are no longer needed.

    Returns:
        dict: Status and results of the cleanup operation
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

        return {
            "status": "success",
            "message": f"Cleaned up {completed_count} completed and {old_count} old records",
            "completed_records": completed_count,
            "old_records": old_count,
        }

    except Exception as e:
        error_msg = f"Error cleaning up resume processing records: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
        }
