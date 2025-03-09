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

from apps.job_seekers.models import JobSeekerProfile
from apps.job_seekers.utils.llm_api import convert_text_resume_to_xml
from apps.job_seekers.utils.resume_parser import (
    extract_text_from_pdf,
    update_profile_from_xml,
)

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


def process_resume(file_path: str, job_seeker_profile_id: int) -> dict[str, Any]:
    """
    Process a resume file to extract information and update the job seeker profile.

    Args:
        file_path: Path to the resume file relative to MEDIA_ROOT.
        job_seeker_profile_id: ID of the JobSeekerProfile to update.

    Returns:
        dict: Result of the processing operation.
    """
    try:
        # Get the profile instance
        try:
            profile = JobSeekerProfile.objects.get(id=job_seeker_profile_id)
        except JobSeekerProfile.DoesNotExist:
            return {
                "success": False,
                "message": "Profile not found",
            }

        # Get absolute path to the PDF file
        absolute_path = default_storage.path(file_path)

        # Step 1: Extract text from PDF
        raw_text = extract_text_from_pdf(absolute_path)
        if not raw_text:
            return {
                "success": False,
                "message": "Failed to extract text from PDF",
            }

        # Step 2: Use LLM to convert raw text to structured XML
        xml_content = convert_text_resume_to_xml(raw_text)
        if not xml_content:
            return {
                "success": False,
                "message": "Failed to process resume text with LLM",
            }

        # Step 3: Update the profile with extracted information
        update_success = update_profile_from_xml(profile, xml_content)
        if not update_success:
            return {
                "success": False,
                "message": "Failed to update profile with extracted data",
            }

        # Step 4: Clean up temporary files
        # Delete the PDF file - it's no longer needed
        try:
            default_storage.delete(file_path)
        except Exception as e:
            logger.warning(f"Failed to delete PDF file: {str(e)}")

        # Return success with profile data
        return {
            "success": True,
            "message": "Resume processed successfully",
            "profile_data": {
                "skills": profile.skills_list,
                "years_of_experience": profile.years_of_experience,
                "current_position": profile.current_position,
            },
        }

    except Exception as e:
        logger.error(f"Error processing resume: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"Error processing resume: {str(e)}",
        }


def handle_resume_upload_task(
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
        # Process the resume
        result = process_resume(uploaded_file_path, job_seeker_profile_id)

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
