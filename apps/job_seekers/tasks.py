"""
Tasks for asynchronous processing in the job_seekers app.

This module contains Django Q2 tasks for handling asynchronous processing of
job seeker-related actions, such as resume parsing and profile creation.
"""

import time
from typing import Any

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile

from apps.job_seekers.models import JobSeekerProfile


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


def process_resume(
    file_path: str, job_seeker_profile_id: int, original_filename: str
) -> dict[str, Any]:
    """
    Process a resume file and extract information.

    This is a placeholder implementation that simulates processing delay
    and returns fake extracted data.

    Args:
        file_path: Path to the resume file relative to MEDIA_ROOT.
        job_seeker_profile_id: ID of the JobSeekerProfile to update.
        original_filename: Original name of the uploaded file.

    Returns:
        dict: Extracted information from the resume.
    """
    # Simulate processing time
    time.sleep(3)

    # Get the profile instance
    try:
        profile = JobSeekerProfile.objects.get(id=job_seeker_profile_id)
    except JobSeekerProfile.DoesNotExist:
        return {
            "success": False,
            "message": "Profile not found",
        }

    # Simulate extracting skills and experience
    # In a real implementation, this would analyze the resume content
    fake_skills = [
        "Python",
        "Django",
        "JavaScript",
        "React",
        "Docker",
        "AWS",
        "SQL",
        "Data Analysis",
    ]
    fake_years_experience = 3

    # Update the profile with the extracted information
    profile.skills = ", ".join(fake_skills)
    profile.years_of_experience = fake_years_experience
    profile.save()

    # Return the extracted information
    return {
        "success": True,
        "message": "Resume processed successfully",
        "profile_data": {
            "skills": fake_skills,
            "years_of_experience": fake_years_experience,
        },
    }


def handle_resume_upload_task(
    uploaded_file_path: str, job_seeker_profile_id: int, original_filename: str
) -> dict[str, Any]:
    """
    Django Q2 task to process a resume file asynchronously.

    Args:
        uploaded_file_path: Path to the temporary uploaded file.
        job_seeker_profile_id: ID of the JobSeekerProfile to update.
        original_filename: Original name of the uploaded file.

    Returns:
        dict: Result of the processing operation.
    """
    try:
        # Process the resume
        result = process_resume(
            uploaded_file_path, job_seeker_profile_id, original_filename
        )

        return {
            "status": "success" if result["success"] else "error",
            "message": result.get("message", ""),
            "profile_data": result.get("profile_data", {}),
        }

    except Exception as e:
        # Log the error
        return {
            "status": "error",
            "message": f"Error processing resume: {str(e)}",
        }
