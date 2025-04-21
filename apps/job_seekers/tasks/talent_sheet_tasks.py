"""
Background tasks for generating talent sheets for job seekers.
"""

import logging
from typing import Any

from apps.job_seekers.models import JobSeekerProfile, RoleRecommendation
from apps.job_seekers.services.recommendation.llm_processor import generate_talent_sheet
from apps.job_seekers.services.talent_pool_manager import TalentPoolManager

# Set up logging
logger = logging.getLogger(__name__)


def generate_talent_sheet_task(job_seeker_profile_id: int) -> dict[str, Any]:
    """
    Generate a talent sheet for a job seeker.

    This function creates a comprehensive talent sheet for a job seeker profile,
    summarizing their skills, experience, and career goals in a recruiter-friendly format.
    The talent sheet is generated using LLM, ensuring high-quality content that effectively
    highlights the candidate's qualifications.

    Args:
        job_seeker_profile_id: ID of the JobSeekerProfile to generate a talent sheet for

    Returns:
        Dictionary with generation results
    """
    try:
        # Get the profile
        profile = JobSeekerProfile.objects.get(id=job_seeker_profile_id)
    except JobSeekerProfile.DoesNotExist:
        error_msg = f"Profile not found: id={job_seeker_profile_id}"
        logger.error(error_msg)
        return {
            "success": False,
            "message": error_msg,
        }

    # Check if we have resume data
    if not profile.resume_xml:
        logger.error(
            "No resume XML data available for profile ID %s", job_seeker_profile_id
        )
        return {
            "success": False,
            "message": "No resume data available for talent sheet generation",
        }

    # Get the user's email for logging
    user_email = (
        profile.user_owner.email if profile.user_owner else "unknown@example.com"
    )
    logger.info("Generating talent sheet for job seeker: %s", user_email)

    try:
        # Get interested roles if available
        interested_roles = []
        role_recs = RoleRecommendation.objects.filter(
            job_seeker=profile, is_candidate_interested=True
        )
        if role_recs.exists():
            interested_roles = list(role_recs.values_list("role_title", flat=True))
            logger.info(
                "Found %d interested roles for talent sheet generation",
                len(interested_roles),
            )

        # Generate talent sheet using LLM
        talent_sheet = generate_talent_sheet(profile.resume_xml, interested_roles)

        # Create or update the talent sheet with the LLM-generated content
        saved_talent_sheet = TalentPoolManager.create_or_update_talent_sheet(
            profile,
            {
                "promotional_blurb": talent_sheet.promotional_blurb,
                "skill_overview": talent_sheet.skill_overview,
                "ideal_roles": talent_sheet.ideal_roles,
                "personal_tagline": profile.personal_tagline,
                "is_published": True,  # Publish it now that we have real content
            },
        )

        logger.info(
            "Created/updated talent sheet with LLM-generated content for %s", user_email
        )

        return {
            "success": True,
            "message": "Generated talent sheet successfully",
            "talent_sheet_id": saved_talent_sheet.pk,
            "profile_id": job_seeker_profile_id,
        }

    except Exception as e:
        error_msg = f"Error generating talent sheet: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "message": error_msg,
        }
