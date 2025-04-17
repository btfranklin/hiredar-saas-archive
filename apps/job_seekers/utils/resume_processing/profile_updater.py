"""
Profile update utilities for resume processing.

This module contains functions for updating job seeker profiles with
data extracted from resumes.
"""

import logging
from typing import Any

from django.db import transaction

from apps.job_seekers.models import JobSeekerProfile

# Setup logging
logger = logging.getLogger(__name__)


def update_profile(
    profile: JobSeekerProfile,
    parsed_data: dict[str, Any],
    xml_content: str | None = None,
) -> bool:
    """
    Update a JobSeekerProfile with data extracted from a resume.

    Args:
        profile: JobSeekerProfile to update
        parsed_data: Dictionary of parsed data from the resume
        xml_content: Optional raw XML content from the resume

    Returns:
        True if the profile was updated successfully, False otherwise
    """
    try:
        with transaction.atomic():
            # Update profile fields
            _update_profile_fields(profile, parsed_data)

            # Update XML if provided - do this before save to call save only once
            if xml_content:
                profile.resume_xml = xml_content

            # Save the profile once with all changes
            profile.save()

            logger.info("Profile updated successfully with parsed resume data")
            return True
    except Exception as e:
        logger.error("Error updating profile from parsed data: %s", str(e))
        return False


def _update_profile_fields(profile: JobSeekerProfile, data: dict[str, Any]) -> None:
    """
    Update specific fields on a JobSeekerProfile from parsed resume data.

    Args:
        profile: JobSeekerProfile to update
        data: Dictionary of parsed data from the resume
    """
    # Update basic profile fields
    if "name" in data.get("personal_details", {}):
        profile.personal_tagline = f"{data['personal_details']['name']}"

    # Update skills as a pipe-separated list
    if "skills" in data:
        profile.skills = data["skills"]

    # Update experience fields
    if "experience" in data:
        profile.experience = data["experience"]

    # Update education
    if "education" in data:
        profile.education = data["education"]

    # Update certifications
    if "certifications" in data:
        profile.certifications = data["certifications"]

    # Update years of experience
    if "years_of_experience" in data:
        profile.years_of_experience = data["years_of_experience"]

    # Update most recent job title
    if "most_recent_title" in data:
        profile.most_recent_title = data["most_recent_title"]

    # Update professional summary
    if "professional_summary" in data:
        profile.professional_summary = data["professional_summary"]

    # Update personal details (applicable to user-owned profiles)
    if profile.user_owner and "personal_details" in data:
        personal_details = data["personal_details"]

        # Update user name if available
        if "name" in personal_details:
            profile.user_owner.name = personal_details["name"]
            profile.user_owner.save()

        # Update location
        if "location" in personal_details:
            profile.location = personal_details["location"]

        # Update phone
        if "phone" in personal_details:
            profile.phone = personal_details["phone"]

    # The update_profile function will handle saving the profile
