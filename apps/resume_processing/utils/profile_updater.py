"""
Profile update utilities for resume processing.

This module contains functions for updating job seeker profiles with
data extracted from resumes.
"""

import logging
from typing import Any

from apps.job_seekers.models import JobSeekerProfile
from apps.job_seekers.services.recommendation.llm_processor import (
    generate_personal_tagline,
)

# Setup logging
logger = logging.getLogger(__name__)


# Add helper to truncate string fields based on max_length
def _truncate_string_fields(instance):
    """Truncate any string attribute on instance that corresponds to a model field with max_length."""
    try:
        # Only proceed if instance has Django _meta with fields attribute
        meta = getattr(instance, "_meta", None)
        if not meta or not hasattr(meta, "fields"):
            return
        for field in meta.fields:
            max_length = getattr(field, "max_length", None)
            value = getattr(instance, field.name, None)
            # Truncate if it's a string exceeding max_length
            if max_length and isinstance(value, str) and len(value) > max_length:
                logger.info(
                    "Truncating field %s to max length %s", field.name, max_length
                )
                setattr(instance, field.name, value[:max_length])
    except Exception as exc:
        # In tests or unexpected cases, skip truncation
        logger.debug(
            "Skipping truncation for instance %r due to error: %s", instance, exc
        )


def update_profile_fields(
    profile: JobSeekerProfile, parsed_data: dict[str, Any]
) -> bool:
    """
    Update only the parsed data fields on the profile without generating a tagline.
    Uses a transaction and ensures only one profile is modified.
    """
    try:
        # Update fields directly on the provided profile instance
        _update_profile_fields(profile, parsed_data)
        # Ensure location not null/empty – handle None safely
        current_location = (getattr(profile, "location", None) or "").strip()
        if not current_location:
            profile.location = "Not provided"

        # Truncate any string fields to their max_length to avoid DB errors
        _truncate_string_fields(profile)
        profile.save()
        return True
    except Exception as e:
        logger.error("Error updating profile fields: %s", str(e))
        return False


def generate_and_save_personal_tagline(
    profile: JobSeekerProfile, xml_content: str, parsed_data: dict[str, Any]
) -> bool:
    """
    Generate a personal tagline from XML, apply fallback logic, and save to profile.
    Uses a transaction and ensures only one profile is modified.
    """
    try:
        # Update the resume XML content
        profile.resume_xml = xml_content
        try:
            tagline = generate_personal_tagline(xml_content)
            profile.personal_tagline = tagline
            logger.info("Personal tagline generated: %s", tagline)
        except Exception as e:
            logger.error("Error generating personal tagline: %s", str(e))
            # Fallback to most recent title or generic
            if parsed_data.get("most_recent_title"):
                profile.personal_tagline = (
                    f"Experienced {parsed_data['most_recent_title']}"
                )
            else:
                profile.personal_tagline = "Job Seeker"
            logger.info("Fallback personal tagline: %s", profile.personal_tagline)
        # Ensure location not null/empty – handle None safely
        current_location = (getattr(profile, "location", None) or "").strip()
        if not current_location:
            profile.location = "Not provided"

        # Truncate any string fields to their max_length to avoid DB errors
        _truncate_string_fields(profile)
        profile.save()
        return True
    except Exception as e:
        logger.error("Error saving personal tagline: %s", str(e))
        return False


def _update_profile_fields(profile: JobSeekerProfile, data: dict[str, Any]) -> None:
    """
    Update specific fields on a JobSeekerProfile from parsed resume data.

    Args:
        profile: JobSeekerProfile to update
        data: Dictionary of parsed data from the resume
    """

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

    # Update personal details
    if "personal_details" in data:
        personal_details = data["personal_details"]

        # Update location
        if "location" in personal_details:
            profile.location = personal_details["location"]

        # Update phone
        if "phone" in personal_details:
            profile.phone = personal_details["phone"]

        # Update the candidate name, for both user-owned and pool-owned profiles
        if "name" in personal_details:
            profile.candidate_name = personal_details["name"]

        # For user-owned profiles, update the user's name
        if profile.user_owner and "name" in personal_details:
            profile.user_owner.name = personal_details["name"]
            profile.user_owner.save()

    # The update_profile function will handle saving the profile
