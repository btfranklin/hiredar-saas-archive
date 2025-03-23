"""
Job processing tasks for recruiters.

This module contains Django Q async tasks for processing job descriptions
and creating job openings from text. Hook functions for task completion
are in the hooks.py module.
"""

import logging
from typing import Any

from apps.recruiters.models import RecruiterProfile
from apps.recruiters.utils.job_processing.pipeline import process_job_description

# Setup logging
logger = logging.getLogger(__name__)


def handle_job_description_task(
    task_id: str, job_title: str, job_description: str, recruiter_profile_id: int
) -> dict[str, Any]:
    """
    Django Q task to process a job description asynchronously.

    Args:
        task_id: The task ID for tracking progress
        job_title: The title of the job
        job_description: The full text description of the job
        recruiter_profile_id: The ID of the RecruiterProfile

    Returns:
        dict: Result of the processing operation
    """
    try:
        # Get the recruiter profile
        try:
            recruiter_profile = RecruiterProfile.objects.get(pk=recruiter_profile_id)
        except RecruiterProfile.DoesNotExist:
            error_msg = f"Recruiter profile not found: id={recruiter_profile_id}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
            }

        # Process the job description using the pipeline
        result = process_job_description(
            task_id, job_title, job_description, recruiter_profile
        )

        return {
            "status": result.get("status", "error"),
            "message": result.get("message", ""),
            "job_opening_id": result.get("job_opening_id"),
        }

    except Exception as e:
        # Log the error
        logger.error("Error processing job description: %s", str(e), exc_info=True)
        return {
            "status": "error",
            "message": f"Error processing job description: {str(e)}",
        }
