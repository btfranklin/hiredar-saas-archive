"""
Resume processing pipeline orchestration.

This module defines the complete resume processing pipeline and provides
both synchronous and asynchronous execution options.
"""

import logging
from typing import Any, Dict

from django.core.files.storage import default_storage

from apps.job_seekers.models import JobSeekerProfile
from apps.job_seekers.utils.resume_processing.extraction import extract_text_from_pdf
from apps.job_seekers.utils.resume_processing.llm_processor import convert_text_to_xml
from apps.job_seekers.utils.resume_processing.profile_updater import update_profile
from apps.job_seekers.utils.resume_processing.xml_parser import parse_resume_xml

# Setup logging
logger = logging.getLogger(__name__)


def process_resume_sync(file_path: str, profile: JobSeekerProfile) -> Dict[str, Any]:
    """
    Process a resume file synchronously, updating the job seeker profile.

    Args:
        file_path: Path to the resume file
        profile: The JobSeekerProfile to update

    Returns:
        Dictionary with success status and result details
    """
    try:
        # Get absolute path to the file
        absolute_path = default_storage.path(file_path)

        # Step 1: Extract text from PDF
        raw_text = extract_text_from_pdf(absolute_path)
        if not raw_text:
            return {"success": False, "message": "Failed to extract text from PDF"}

        # Step 2: Convert text to structured XML using LLM
        xml_content = convert_text_to_xml(raw_text)
        if not xml_content:
            return {"success": False, "message": "Failed to convert resume to XML"}

        # Step 3: Parse XML into structured data
        parsed_data = parse_resume_xml(xml_content)
        if not parsed_data:
            return {"success": False, "message": "Failed to parse XML data"}

        # Step 4: Update profile with parsed data
        update_success = update_profile(profile, parsed_data, xml_content)
        if not update_success:
            return {
                "success": False,
                "message": "Failed to update profile with extracted data",
            }

        # Clean up temp file
        default_storage.delete(file_path)

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
        logger.error(f"Error processing resume: {str(e)}")
        return {"success": False, "message": f"Error processing resume: {str(e)}"}


async def process_resume_async(file_path: str, profile_id: int) -> Dict[str, Any]:
    """
    Process a resume file asynchronously in a Django Q task.

    This is a wrapper around the synchronous function that handles the task context.

    Args:
        file_path: Path to the resume file
        profile_id: ID of the JobSeekerProfile to update

    Returns:
        Dictionary with task result
    """
    try:
        # Get the profile
        try:
            profile = JobSeekerProfile.objects.get(id=profile_id)
        except JobSeekerProfile.DoesNotExist:
            return {"success": False, "message": "Profile not found"}

        # Process the resume
        return process_resume_sync(file_path, profile)

    except Exception as e:
        logger.error(f"Error in async task: {str(e)}")
        return {"success": False, "message": f"Error in async task: {str(e)}"}
