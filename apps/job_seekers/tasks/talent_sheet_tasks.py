"""
Background tasks for generating talent sheets for job seekers.
"""

import logging
from typing import Any

from celery import shared_task

from apps.job_seekers.models import JobSeekerProfile, RoleRecommendation, TalentSheet
from apps.job_seekers.services.recommendation.llm_processor import generate_talent_sheet
from apps.job_seekers.services.talent_pool_manager import TalentPoolManager

# Set up logging
logger = logging.getLogger(__name__)


@shared_task(
    name="apps.job_seekers.tasks.talent_sheet_tasks.generate_talent_sheet_task"
)
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
            "status": "error",
            "message": error_msg,
            "profile_id": job_seeker_profile_id,
        }

    # Fail-fast: skip if a talent sheet already exists for this profile
    try:
        existing_sheet = TalentSheet.objects.get(job_seeker=profile)
        logger.info(
            "Talent sheet already exists for profile %s – skipping generation",
            job_seeker_profile_id,
        )
        return {
            "status": "success",
            "message": "Talent sheet already exists",
            "talent_sheet_id": existing_sheet.pk,
            "profile_id": job_seeker_profile_id,
        }
    except TalentSheet.DoesNotExist:
        pass

    # Check if we have resume data
    if not profile.resume_xml:
        logger.error(
            "No resume XML data available for profile ID %s", job_seeker_profile_id
        )
        return {
            "status": "error",
            "message": "No resume data available for talent sheet generation",
            "profile_id": job_seeker_profile_id,
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
        talent_sheet = generate_talent_sheet(profile, interested_roles)

        # Build qualifications string from education and certifications
        education = profile.education or ""
        certifications = profile.certifications or ""
        qualifications_parts: list[str] = []
        if education:
            qualifications_parts.append(education.strip())
        if certifications:
            qualifications_parts.append(certifications.strip())
        qualifications = "\n\n".join(qualifications_parts)

        # Create or update the talent sheet with the LLM-generated content
        saved_talent_sheet = TalentPoolManager.create_or_update_talent_sheet(
            profile,
            {
                "promotional_blurb": talent_sheet.promotional_blurb,
                "experience_overview": talent_sheet.experience_overview,
                "ideal_roles": talent_sheet.ideal_roles,
                "skills": profile.skills or "",
                "qualifications": qualifications,
                "personal_tagline": profile.personal_tagline,
                "is_published": True,  # Publish it now that we have real content
            },
        )

        logger.info(
            "Created/updated talent sheet with LLM-generated content for %s", user_email
        )

        return {
            "status": "success",
            "message": "Generated talent sheet successfully",
            "talent_sheet_id": saved_talent_sheet.pk,
            "profile_id": job_seeker_profile_id,
        }

    except Exception as e:
        error_msg = f"Error generating talent sheet: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "profile_id": job_seeker_profile_id,
        }
