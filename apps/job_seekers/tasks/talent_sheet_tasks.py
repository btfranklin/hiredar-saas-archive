"""
Talent sheet generation tasks for job seekers.

This module contains Django Q2 tasks for generating talent sheets for job seekers
who opt into the talent pool.
"""

import logging
from typing import Any

from django.db import transaction

from apps.job_seekers.models import JobSeekerProfile, RoleRecommendation, TalentSheet
from apps.job_seekers.utils.recommendation.llm_processor import generate_talent_sheet

# Setup logging
logger = logging.getLogger(__name__)


def generate_talent_sheet_task(job_seeker_profile_id: int) -> dict[str, Any]:
    """
    Django Q2 task to generate a talent sheet for a job seeker who enters the talent pool.

    This task analyzes the job seeker's profile, resume data, and interested roles
    to create a comprehensive talent sheet for recruiters to view.

    Args:
        job_seeker_profile_id: ID of the JobSeekerProfile to generate a talent sheet for

    Returns:
        dict: Result of the talent sheet generation operation
    """
    try:
        # Get the job seeker profile
        try:
            profile = JobSeekerProfile.objects.get(id=job_seeker_profile_id)
        except JobSeekerProfile.DoesNotExist:
            error_msg = f"Profile not found: id={job_seeker_profile_id}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
            }

        # Log the start of processing
        logger.info("Generating talent sheet for job seeker: %s", profile.user.email)

        # Check if we have resume XML data
        if not profile.resume_xml:
            logger.warning(
                "No resume XML data available for profile ID %s", job_seeker_profile_id
            )
            return {
                "success": False,
                "message": "Cannot generate talent sheet: No resume data available",
            }

        # Get interested roles (from RoleRecommendation objects)
        interested_roles = list(
            RoleRecommendation.objects.filter(
                job_seeker=profile, is_candidate_interested=True
            ).values_list("role_title", flat=True)
        )

        logger.info(
            "Found %d interested roles for profile ID %s",
            len(interested_roles),
            job_seeker_profile_id,
        )

        # Generate the talent sheet using the LLM processor
        try:
            talent_sheet = generate_talent_sheet(
                resume_xml=profile.resume_xml,
                interested_roles=interested_roles if interested_roles else None,
            )

            # Associate the talent sheet with the job seeker profile
            talent_sheet.job_seeker = profile

            # Save the talent sheet to the database
            with transaction.atomic():
                # Delete any existing talent sheet for this profile to avoid duplicates
                TalentSheet.objects.filter(job_seeker=profile).delete()

                # Save the new talent sheet
                talent_sheet.save()

            logger.info("Successfully created talent sheet for %s", profile.user.email)

            # TODO: Submit a job to the Matching app for further AI processing
            # from apps.matching.tasks import process_candidate_matches
            # process_candidate_matches.delay(job_seeker_profile_id=job_seeker_profile_id)

            return {
                "success": True,
                "message": "Talent sheet generated successfully",
                "profile_id": job_seeker_profile_id,
            }

        except Exception as e:
            logger.error(
                "Error in LLM talent sheet generation: %s",
                str(e),
                exc_info=True,
            )
            return {
                "success": False,
                "message": f"Error generating talent sheet: {str(e)}",
            }

    except Exception as e:
        # Log the error
        logger.error("Error generating talent sheet: %s", str(e), exc_info=True)
        return {
            "success": False,
            "message": f"Error generating talent sheet: {str(e)}",
        }
