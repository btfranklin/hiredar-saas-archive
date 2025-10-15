"""
Profile update utilities for resume processing.

This module contains functions for updating candidate profiles with
data extracted from resumes.
"""

import logging
from typing import Any

from apps.candidates.models import CandidateProfile
from apps.candidates.services.recommendation.llm_processor import (
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
    profile: CandidateProfile, parsed_data: dict[str, Any]
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
    profile: CandidateProfile, xml_content: str, parsed_data: dict[str, Any]
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
            logger.warning("Error generating personal tagline: %s", str(e))
            # Fallback to most recent title or generic
            if parsed_data.get("most_recent_title"):
                profile.personal_tagline = (
                    f"Experienced {parsed_data['most_recent_title']}"
                )
            else:
                profile.personal_tagline = "Candidate"
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


def _update_profile_fields(profile: CandidateProfile, data: dict[str, Any]) -> None:
    """
    Update specific fields on a CandidateProfile from parsed resume data.

    Args:
        profile: CandidateProfile to update
        data: Dictionary of parsed data from the resume
    """

    # Update skills as a pipe-separated list
    if "skills" in data and data["skills"] is not None:
        profile.skills = data["skills"]

    # Update experience fields
    if "experience" in data and data["experience"] is not None:
        profile.experience = data["experience"]

    # Update education
    if "education" in data and data["education"] is not None:
        profile.education = data["education"]

    # Update certifications
    if "certifications" in data and data["certifications"] is not None:
        profile.certifications = data["certifications"]

    # Update years of experience
    if "years_of_experience" in data and data["years_of_experience"] is not None:
        profile.years_of_experience = data["years_of_experience"]

    # Update most recent job title
    if "most_recent_title" in data and data["most_recent_title"] is not None:
        profile.most_recent_title = data["most_recent_title"]

    # Update professional summary
    if "professional_summary" in data and data["professional_summary"] is not None:
        profile.professional_summary = data["professional_summary"]

    # Update personal details
    if "personal_details" in data and data["personal_details"] is not None:
        personal_details = data["personal_details"]

        # Update location
        if "location" in personal_details and personal_details["location"] is not None:
            profile.location = personal_details["location"]

        # Update phone
        if "phone" in personal_details and personal_details["phone"] is not None:
            profile.phone = personal_details["phone"]

        # Update the candidate name when available
        if "name" in personal_details and personal_details["name"] is not None:
            profile.candidate_name = personal_details["name"]

    # The update_profile function will handle saving the profile
