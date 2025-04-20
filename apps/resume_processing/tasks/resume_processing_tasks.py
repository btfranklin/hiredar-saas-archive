"""
Resume processing tasks for job seekers.

This module contains Django Q2 tasks for handling asynchronous processing of
resume uploads and parsing.
"""

import logging
from typing import Any

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile

from apps.job_seekers.models.profile import JobSeekerProfile
from apps.resume_processing.utils.pipeline import process_resume

# Setup logging
logger = logging.getLogger(__name__)


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
