"""
Tasks for asynchronous processing in the job_seekers app.

This module contains Django Q2 tasks for handling asynchronous processing of
job seeker-related actions, such as resume parsing and profile creation.
"""

import logging
from typing import Any

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from django_q.models import Schedule
from django_q.tasks import async_task, schedule

from apps.job_seekers.models import JobSeekerProfile, ResumeProcessingTaskProgress
from apps.job_seekers.utils.resume_processing.pipeline import process_resume

# Setup logging
logger = logging.getLogger(__name__)


# Make sure this is exported at the module level
__all__ = [
    "save_resume_file",
    "handle_resume_upload_task",
    "cleanup_resume_processing_progress",
    "ensure_cleanup_scheduled",
]


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
                != "apps.job_seekers.tasks.cleanup_resume_processing_progress"
            ):
                existing.delete()
                existing = None

        # Create schedule if it doesn't exist
        if not existing:
            schedule(
                "apps.job_seekers.tasks.cleanup_resume_processing_progress",
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


def save_resume_file(resume_file: UploadedFile, filename: str) -> str:
    """
    Save an uploaded resume file to the media directory.

    Args:
        resume_file: The uploaded resume file.
        filename: The name to save the file as.

    Returns:
        str: The path to the saved file relative to MEDIA_ROOT.
    """
    # Create path within the media directory for resumes
    file_path = f"resumes/{filename}"

    # Save the file using Django's storage API
    path = default_storage.save(file_path, ContentFile(resume_file.read()))

    return path


def handle_resume_upload_task(
    uploaded_file_path: str,
    job_seeker_profile_id: int,
    task_id: str | None = None,
) -> dict[str, Any]:
    """
    Django Q2 task to process a resume file asynchronously.

    Args:
        uploaded_file_path: Path to the temporary uploaded file.
        job_seeker_profile_id: ID of the JobSeekerProfile to update.
        task_id: The ID of the task for progress tracking.

    Returns:
        dict: Result of the processing operation.
    """
    try:
        # Process the resume using the unified pipeline
        try:
            profile = JobSeekerProfile.objects.get(id=job_seeker_profile_id)
        except JobSeekerProfile.DoesNotExist:
            error_msg = f"Profile not found: id={job_seeker_profile_id}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
            }

        # Process the resume with progress tracking
        result = process_resume(uploaded_file_path, profile, task_id=task_id)

        return {
            "status": "success" if result.get("success", False) else "error",
            "message": result.get("message", ""),
            "profile_data": result.get("profile_data", {}),
        }

    except Exception as e:
        # Log the error
        logger.error("Error processing resume: %s", str(e), exc_info=True)
        return {
            "status": "error",
            "message": f"Error processing resume: {str(e)}",
        }
