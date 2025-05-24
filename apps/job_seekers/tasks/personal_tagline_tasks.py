"""
Personal tagline tasks for job seekers.

This module contains Celery tasks for generating personal taglines
for job seekers based on their profile data.
"""

import logging
from typing import Any

from celery import shared_task

from apps.job_seekers.models import JobSeekerProfile
from apps.job_seekers.services.recommendation.llm_processor import (
    generate_personal_tagline as generate_tagline_from_xml,
)

# Setup logging
logger = logging.getLogger(__name__)


@shared_task(
    name="apps.job_seekers.tasks.personal_tagline_tasks.generate_personal_tagline"
)
def generate_personal_tagline(job_seeker_profile_id: int) -> dict[str, Any]:
    """
    Generate a personal tagline for a job seeker based on their profile.

    This task creates a concise, professional tagline that highlights the
    job seeker's key strengths, skills, and career focus.

    Idempotency & concurrency:
        The generated value *overwrites* the existing ``personal_tagline``
        field, therefore the task is idempotent.  Concurrent runs are safe –
        the last write wins – but they do waste tokens; upstream callers
        should still de‑duplicate schedule requests.

    Args:
        job_seeker_profile_id: ID of the JobSeekerProfile to generate a tagline for

    Returns:
        dict: Result of the tagline generation operation
    """
    try:
        # Get the job seeker profile
        try:
            profile = JobSeekerProfile.objects.get(id=job_seeker_profile_id)
        except JobSeekerProfile.DoesNotExist:
            error_msg = f"Profile not found: id={job_seeker_profile_id}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "profile_id": job_seeker_profile_id,
            }

        # Log the start of processing
        logger.info(
            "Generating personal tagline for job seeker: %s",
            profile.user_owner.email if profile.user_owner else "Unknown",
        )

        # Check if we have resume XML data
        if not profile.resume_xml:
            logger.warning(
                "No resume XML data available for profile ID %s", job_seeker_profile_id
            )
            return {
                "status": "error",
                "message": "Cannot generate tagline: No resume data available",
                "profile_id": job_seeker_profile_id,
            }

        # Validate XML content
        resume_xml = profile.resume_xml
        logger.info(
            "Resume XML found, length: %d characters",
            len(resume_xml) if resume_xml else 0,
        )

        # Generate the tagline using the LLM processor
        try:
            tagline = generate_tagline_from_xml(resume_xml)

            # Save the tagline to the user's profile
            profile.personal_tagline = tagline
            profile.save(update_fields=["personal_tagline"])

            logger.info(
                "Generated tagline for %s: %s",
                profile.user_owner.email if profile.user_owner else "Unknown",
                tagline,
            )

            return {
                "status": "success",
                "message": "Personal tagline generated successfully",
                "profile_id": job_seeker_profile_id,
                "tagline": tagline,
            }

        except Exception as e:
            logger.error("Error in LLM tagline generation: %s", str(e), exc_info=True)
            return {
                "status": "error",
                "message": f"Error generating tagline: {str(e)}",
                "profile_id": job_seeker_profile_id,
            }

    except Exception as e:
        # Log the error
        logger.error("Error generating personal tagline: %s", str(e), exc_info=True)
        return {
            "status": "error",
            "message": f"Error generating personal tagline: {str(e)}",
            "profile_id": job_seeker_profile_id,
        }
