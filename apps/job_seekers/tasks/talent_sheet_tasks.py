"""
Background tasks for generating talent sheets for job seekers.
"""

import logging
from typing import Any

from apps.job_seekers.models import JobSeekerProfile
from apps.job_seekers.services.talent_pool_manager import TalentPoolManager

# Set up logging
logger = logging.getLogger(__name__)


def generate_talent_sheet_task(job_seeker_profile_id: int) -> dict[str, Any]:
    """
    Generate a talent sheet for a job seeker.

    This function creates a comprehensive talent sheet for a job seeker profile,
    summarizing their skills, experience, and career goals in a recruiter-friendly format.

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

    # Create the talent sheet data
    talent_sheet_data = {}

    # Craft promotional blurb
    if profile.most_recent_title or profile.years_of_experience:
        blurb_parts = []
        if profile.most_recent_title:
            blurb_parts.append(f"Experienced {profile.most_recent_title}")
        if profile.years_of_experience:
            blurb_parts.append(
                f"with {profile.years_of_experience}+ years of experience"
            )

        blurb = " ".join(blurb_parts)
        if profile.professional_summary:
            blurb += f". {profile.professional_summary.split('.')[0]}."

        talent_sheet_data["promotional_blurb"] = blurb
    else:
        talent_sheet_data["promotional_blurb"] = (
            "Talented professional with a proven track record of success."
        )

    # Craft skill overview
    if profile.skills:
        skills_list = profile.skills_list[:5]  # Get top 5 skills
        if skills_list:
            talent_sheet_data["skill_overview"] = (
                f"Key skills include {', '.join(skills_list)}."
            )
        else:
            talent_sheet_data["skill_overview"] = (
                "Versatile skill set applicable to various technical roles."
            )
    else:
        talent_sheet_data["skill_overview"] = (
            "Versatile skill set applicable to various technical roles."
        )

    # Set published status (default to published when explicitly created)
    talent_sheet_data["is_published"] = True

    try:
        # Create or update the talent sheet
        talent_sheet = TalentPoolManager.create_or_update_talent_sheet(
            profile, talent_sheet_data
        )

        # In a real implementation, we might want to trigger candidate matching
        # after creating the talent sheet
        # process_candidate_matches.delay(job_seeker_profile_id=job_seeker_profile_id)

        logger.info("Successfully created talent sheet for %s", user_email)

        return {
            "success": True,
            "message": "Generated talent sheet successfully",
            "talent_sheet_id": talent_sheet.pk,
            "profile_id": job_seeker_profile_id,
        }

    except Exception as e:
        error_msg = f"Error generating talent sheet: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "message": error_msg,
        }
