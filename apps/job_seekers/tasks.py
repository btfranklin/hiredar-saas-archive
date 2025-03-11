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

from apps.job_seekers.utils.resume_processing import process_resume_async

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


async def handle_resume_upload_task(
    uploaded_file_path: str, job_seeker_profile_id: int
) -> dict[str, Any]:
    """
    Django Q2 task to process a resume file asynchronously.

    Args:
        uploaded_file_path: Path to the temporary uploaded file.
        job_seeker_profile_id: ID of the JobSeekerProfile to update.

    Returns:
        dict: Result of the processing operation.
    """
    try:
        # Process the resume using the unified pipeline
        result = await process_resume_async(uploaded_file_path, job_seeker_profile_id)

        return {
            "status": "success" if result["success"] else "error",
            "message": result.get("message", ""),
            "profile_data": result.get("profile_data", {}),
        }

    except Exception as e:
        # Log the error
        logger.error(f"Error processing resume: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Error processing resume: {str(e)}",
        }
