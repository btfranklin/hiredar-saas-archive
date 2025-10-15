"""
Helpers for updating candidate profiles during resume ingestion.
"""

from __future__ import annotations

import logging
from typing import Any

from apps.candidates.models import CandidateProfile
from apps.candidates.services.recommendation.llm_processor import (
    generate_personal_tagline,
)

logger = logging.getLogger(__name__)


def _truncate_string_fields(instance: CandidateProfile) -> None:
    """
    Ensure CharField/TextField values do not exceed their max_length constraints.
    """
    meta = getattr(instance, "_meta", None)
    if not meta or not hasattr(meta, "fields"):
        return

    for field in meta.fields:
        max_length = getattr(field, "max_length", None)
        value = getattr(instance, field.name, None)
        if max_length and isinstance(value, str) and len(value) > max_length:
            setattr(instance, field.name, value[:max_length])


def update_profile_fields(
    profile: CandidateProfile,
    parsed_data: dict[str, Any],
) -> bool:
    """
    Update structured resume fields on ``profile`` using parsed resume data.
    """
    try:
        _apply_parsed_data(profile, parsed_data)

        current_location = (getattr(profile, "location", None) or "").strip()
        if not current_location:
            profile.location = "Not provided"

        _truncate_string_fields(profile)
        profile.save()
        return True
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error updating candidate profile fields: %s", exc)
        return False


def generate_and_save_personal_tagline(
    profile: CandidateProfile,
    xml_content: str,
    parsed_data: dict[str, Any],
) -> bool:
    """
    Generate a personal tagline from XML and persist it on the profile.
    """
    try:
        profile.resume_xml = xml_content
        try:
            tagline = generate_personal_tagline(xml_content)
            profile.personal_tagline = tagline
        except Exception as exc:  # pragma: no cover - fallback path
            logger.warning("Failed to generate personal tagline: %s", exc)
            if parsed_data.get("most_recent_title"):
                profile.personal_tagline = (
                    f"Experienced {parsed_data['most_recent_title']}"
                )
            else:
                profile.personal_tagline = "Candidate"

        current_location = (getattr(profile, "location", None) or "").strip()
        if not current_location:
            profile.location = "Not provided"

        _truncate_string_fields(profile)
        profile.save()
        return True
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error saving personal tagline: %s", exc)
        return False


def _apply_parsed_data(
    profile: CandidateProfile,
    data: dict[str, Any],
) -> None:
    """Map parsed resume fields onto the CandidateProfile instance."""
    if "skills" in data and data["skills"] is not None:
        profile.skills = data["skills"]

    if "experience" in data and data["experience"] is not None:
        profile.experience = data["experience"]

    if "education" in data and data["education"] is not None:
        profile.education = data["education"]

    if "certifications" in data and data["certifications"] is not None:
        profile.certifications = data["certifications"]

    if "years_of_experience" in data and data["years_of_experience"] is not None:
        profile.years_of_experience = data["years_of_experience"]

    if "most_recent_title" in data and data["most_recent_title"] is not None:
        profile.most_recent_title = data["most_recent_title"]

    if "desired_role" in data and data["desired_role"] is not None:
        profile.desired_role = data["desired_role"]

    if "professional_summary" in data and data["professional_summary"] is not None:
        profile.professional_summary = data["professional_summary"]

    if "personal_details" in data and data["personal_details"] is not None:
        personal_details = data["personal_details"]
        if "location" in personal_details and personal_details["location"] is not None:
            profile.location = personal_details["location"]

        if "phone" in personal_details and personal_details["phone"] is not None:
            profile.phone = personal_details["phone"][:30]

        if "name" in personal_details and personal_details["name"] is not None:
            profile.candidate_name = personal_details["name"]

