"""
Tasks for generating role recommendations for candidate profiles.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

from apps.candidates.models import CandidateProfile, CandidateRoleRecommendation
from apps.candidates.services.profile_service import CandidateProfileService
from apps.candidates.services.recommendation.llm_processor import (
    generate_role_recommendations as generate_role_recommendations_from_xml,
)

logger = logging.getLogger(__name__)


@shared_task(
    name="apps.candidates.tasks.recommendation_tasks.generate_role_recommendations"
)
def generate_role_recommendations(
    input_data: dict[str, Any] | int | None = None,
) -> dict[str, Any]:
    """
    Generate role recommendations for the given CandidateProfile.
    """
    if isinstance(input_data, dict):
        candidate_profile_id = input_data.get("profile_id")
        if candidate_profile_id is None:
            return {
                "status": "error",
                "message": "No profile_id found in input data",
                "input_data": input_data,
            }
    elif isinstance(input_data, int):
        candidate_profile_id = input_data
    else:
        return {"status": "error", "message": "No input provided"}

    try:
        profile = CandidateProfile.objects.get(pk=candidate_profile_id)
    except CandidateProfile.DoesNotExist:
        error_msg = f"CandidateProfile not found: id={candidate_profile_id}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "profile_id": candidate_profile_id,
        }

    if not profile.resume_xml:
        logger.warning(
            "No resume XML data available for CandidateProfile %s",
            candidate_profile_id,
        )
        return {
            "status": "error",
            "message": "Cannot generate role recommendations: No resume data available",
            "profile_id": candidate_profile_id,
        }

    try:
        recommendations = generate_role_recommendations_from_xml(profile.resume_xml)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(
            "Error generating role recommendations for CandidateProfile %s: %s",
            candidate_profile_id,
            exc,
            exc_info=True,
        )
        return {
            "status": "error",
            "message": f"Error generating role recommendations: {exc}",
            "profile_id": candidate_profile_id,
        }

    if not recommendations:
        logger.warning(
            "No role recommendations generated for CandidateProfile %s",
            candidate_profile_id,
        )
        CandidateRoleRecommendation.objects.filter(
            candidate_profile=profile
        ).delete()
        CandidateProfileService.safe_update_ideal_roles(candidate_profile_id, "")
        return {
            "status": "error",
            "message": "No suitable role recommendations could be generated",
            "profile_id": candidate_profile_id,
        }

    CandidateRoleRecommendation.objects.filter(candidate_profile=profile).delete()
    created_recommendations = []
    for recommendation in recommendations:
        recommendation.candidate_profile = profile
        recommendation.save()
        created_recommendations.append(recommendation)

    CandidateProfileService.safe_update_ideal_roles(
        candidate_profile_id,
        ", ".join(rec.role_title for rec in created_recommendations),
    )

    logger.info(
        "Created %d role recommendations for CandidateProfile %s",
        len(created_recommendations),
        candidate_profile_id,
    )

    return {
        "status": "success",
        "message": "Role recommendations generated successfully",
        "profile_id": candidate_profile_id,
        "recommendations_count": len(created_recommendations),
        "recommendations": [
            {
                "id": rec.id,
                "title": rec.role_title,
                "description": rec.description,
            }
            for rec in created_recommendations
        ],
    }

