"""
Profile update utilities for resume processing.

This module contains functions for updating job seeker profiles with
data extracted from resumes.
"""

import logging
from typing import Any

from apps.job_seekers.models import JobSeekerProfile

# Setup logging
logger = logging.getLogger(__name__)


def update_profile(
    profile: JobSeekerProfile, parsed_data: dict[str, Any], xml_content: str
) -> bool:
    """
    Update a JobSeekerProfile with parsed resume data.

    Args:
        profile: The JobSeekerProfile instance to update
        parsed_data: Dictionary of parsed resume data
        xml_content: Original XML content (for storage)

    Returns:
        True if update was successful, False otherwise
    """
    try:
        # Update skills
        skills = parsed_data.get("skills", [])
        if skills:
            profile.skills = ",".join(skills)

        # Update current position
        current_position = parsed_data.get("current_position")
        if current_position:
            profile.current_position = current_position

        # Update years of experience
        years_experience = parsed_data.get("years_of_experience", 0)
        if years_experience:
            profile.years_of_experience = years_experience

        # Update professional summary
        professional_summary = parsed_data.get("professional_summary")
        if professional_summary:
            profile.professional_summary = professional_summary

        # Store the XML for potential future use
        profile.resume_xml = xml_content

        # Save the profile
        profile.save()

        return True
    except Exception as e:
        logger.error("Error updating profile from parsed data: %s", str(e))
        return False
