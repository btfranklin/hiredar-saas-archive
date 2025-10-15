"""
Background tasks for generating recruiter-facing content on CandidateProfile records.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

from apps.candidates.models import CandidateProfile, CandidateRoleRecommendation
from apps.candidates.services.profile_service import CandidateProfileService
from apps.candidates.services.recommendation.llm_processor import (
    generate_profile_enrichment,
)

logger = logging.getLogger(__name__)


@shared_task(
    name="apps.candidates.tasks.profile_enrichment_tasks.generate_profile_enrichment"
)
def generate_profile_enrichment_task(candidate_profile_id: int) -> dict[str, Any]:
    """
    Generate promotional content and store it on the CandidateProfile record.
    """
    try:
        profile = CandidateProfile.objects.get(pk=candidate_profile_id)
    except CandidateProfile.DoesNotExist:
        error_msg = f"CandidateProfile not found: id={candidate_profile_id}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg, "profile_id": candidate_profile_id}

    if not profile.resume_xml:
        logger.error(
            "No resume XML available for CandidateProfile %s", candidate_profile_id
        )
        return {
            "status": "error",
            "message": "No resume data available for profile enrichment",
            "profile_id": candidate_profile_id,
        }

    interested_roles = list(
        CandidateRoleRecommendation.objects.filter(
            candidate_profile=profile
        ).values_list("role_title", flat=True)
    )

    try:
        enrichment = generate_profile_enrichment(profile, interested_roles)
    except Exception as exc:  # pragma: no cover - defensive
        error_msg = f"Error generating profile enrichment: {exc}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "message": error_msg,
            "profile_id": candidate_profile_id,
        }

    education = profile.education or ""
    certifications = profile.certifications or ""
    qualifications_parts = [part.strip() for part in (education, certifications) if part.strip()]
    qualifications = "\n\n".join(qualifications_parts)

    CandidateProfileService.safe_update_profile_enrichment(
        candidate_profile_id,
        {
            "promotional_blurb": enrichment.promotional_blurb,
            "experience_overview": enrichment.experience_overview,
            "ideal_roles": enrichment.ideal_roles,
            "skills": profile.skills or "",
            "qualifications": qualifications,
            "is_published": True,
        },
    )

    logger.info(
        "Stored profile enrichment content for CandidateProfile %s",
        candidate_profile_id,
    )
    return {
        "status": "success",
        "message": "Generated profile enrichment successfully",
        "profile_id": candidate_profile_id,
    }
