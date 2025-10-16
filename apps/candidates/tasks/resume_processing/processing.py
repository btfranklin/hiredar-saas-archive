"""
Resume processing tasks for candidate profiles.

This module contains Celery tasks for handling asynchronous processing of
resume uploads and parsing.
"""

import logging
from typing import Any

from celery import shared_task
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile

from apps.candidates.models import CandidateProfile

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


@shared_task(
    name="apps.candidates.tasks.resume_processing.processing.handle_resume_upload_task"
)
def handle_resume_upload_task(
    uploaded_file_path: str,
    candidate_profile_id: int,
    task_id: str | None = None,
) -> dict[str, Any]:
    """
    Celery task to process a resume file asynchronously for a ``CandidateProfile``.

    Args:
        uploaded_file_path: Path to the temporary uploaded file.
        candidate_profile_id: ID of the CandidateProfile to update.
        task_id: The ID of the task for progress tracking.

    Returns:
        dict: Result of the processing operation with structured data for chaining.
    """
    try:
        # Process the resume using the unified candidate pipeline
        try:
            profile = CandidateProfile.objects.get(id=candidate_profile_id)
        except CandidateProfile.DoesNotExist:
            error_msg = f"CandidateProfile not found: id={candidate_profile_id}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "profile_id": candidate_profile_id,
            }

        # Process the resume with progress tracking
        # Deferred import to avoid circular import
        from apps.candidates.services.resume_pipeline import process_resume

        result = process_resume(uploaded_file_path, profile, task_id=task_id)

        return {
            "status": "success" if result.get("success", False) else "error",
            "message": result.get("message", ""),
            "profile_data": result.get("profile_data", {}),
            "profile_id": candidate_profile_id,
            "file_path": uploaded_file_path,
            "processing_time": result.get("processing_time"),
            "pipeline_steps": result.get("pipeline_steps", []),
        }

    except Exception as e:
        # Log the error
        logger.error("Error processing resume: %s", str(e), exc_info=True)
        return {
            "status": "error",
            "message": f"Error processing resume: {str(e)}",
            "profile_id": candidate_profile_id,
            "file_path": uploaded_file_path,
        }
