"""
Celery tasks for generating personal taglines for candidate profiles.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

from apps.candidates.models import CandidateProfile
from apps.candidates.services.recommendation.llm_processor import (
    generate_personal_tagline as generate_tagline_from_xml,
)

logger = logging.getLogger(__name__)


@shared_task(
    name="apps.candidates.tasks.personal_tagline_tasks.generate_personal_tagline"
)
def generate_personal_tagline(candidate_profile_id: int) -> dict[str, Any]:
    """
    Generate a personal tagline for the candidate profile identified by ``candidate_profile_id``.
    """
    try:
        profile = CandidateProfile.objects.get(pk=candidate_profile_id)
    except CandidateProfile.DoesNotExist:
        error_msg = f"CandidateProfile not found: id={candidate_profile_id}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg, "profile_id": candidate_profile_id}

    if not profile.resume_xml:
        logger.warning(
            "No résumé XML available for CandidateProfile %s", candidate_profile_id
        )
        return {
            "status": "error",
            "message": "Cannot generate tagline: No résumé data available",
            "profile_id": candidate_profile_id,
        }

    try:
        tagline = generate_tagline_from_xml(profile.resume_xml)
        profile.personal_tagline = tagline
        profile.save(update_fields=["personal_tagline", "updated_at"])

        logger.info(
            "Generated tagline for CandidateProfile %s: %s",
            candidate_profile_id,
            tagline,
        )

        return {
            "status": "success",
            "message": "Personal tagline generated successfully",
            "profile_id": candidate_profile_id,
            "tagline": tagline,
        }
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(
            "Error generating personal tagline for CandidateProfile %s: %s",
            candidate_profile_id,
            exc,
            exc_info=True,
        )
        return {
            "status": "error",
            "message": f"Error generating tagline: {exc}",
            "profile_id": candidate_profile_id,
        }
