"""
Recommendation tasks for job seekers.

This module contains Celery tasks for generating role recommendations
for job seekers.
"""

import logging
from typing import Any

from celery import shared_task

from apps.job_seekers.models import JobSeekerProfile, RoleRecommendation
from apps.job_seekers.services.recommendation.llm_processor import (
    generate_role_recommendations as generate_role_recommendations_from_xml,
)

# Setup logging
logger = logging.getLogger(__name__)


@shared_task(
    name="apps.job_seekers.tasks.recommendation_tasks.generate_role_recommendations"
)
def generate_role_recommendations(
    input_data: dict[str, Any] | int | None = None,
) -> dict[str, Any]:
    """
    Generate role recommendations for a job seeker based on their profile.

    This task analyzes the job seeker's skills, experience, and other profile
    data to generate career role recommendations.

    Idempotency & concurrency:
        The task deletes existing recommendations and creates a fresh set each
        time it runs.  It is therefore *idempotent* but **not** concurrency‑
        safe – parallel executions will race against one another.  Up‑stream
        scheduling logic must ensure at most one active run per profile.

    Args:
        input_data: Can be a dict (from chain), an int (profile_id), or None

    Returns:
        dict: Result of the recommendation operation with structured data
    """
    try:
        # Handle different input types for backward compatibility
        if isinstance(input_data, dict):
            job_seeker_profile_id = input_data.get("profile_id")
            if job_seeker_profile_id is None:
                return {
                    "status": "error",
                    "message": "No profile_id found in input data",
                    "input_data": input_data,
                }
        elif isinstance(input_data, int):
            job_seeker_profile_id = input_data
        elif input_data is None:
            return {"status": "error", "message": "No input provided"}
        else:
            return {
                "status": "error",
                "message": f"Unexpected input type: {type(input_data)}",
                "input_data": input_data,
            }

        # Get the job seeker profile
        try:
            profile = JobSeekerProfile.objects.get(id=job_seeker_profile_id)
        except JobSeekerProfile.DoesNotExist:
            error_msg = f"Profile not found: id={job_seeker_profile_id}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "profile_id": job_seeker_profile_id,
            }

        # Log the start of processing
        logger.info(
            "Generating role recommendations for job seeker: %s",
            profile.user_owner.email if profile.user_owner else "Unknown",
        )

        # Check if we have resume XML data
        if not profile.resume_xml:
            logger.warning(
                "No resume XML data available for profile ID %s", job_seeker_profile_id
            )
            return {
                "status": "error",
                "message": "Cannot generate role recommendations: No resume data available",
                "profile_id": job_seeker_profile_id,
            }

        # Validate XML content
        resume_xml = profile.resume_xml
        logger.info(
            "Resume XML found, length: %d characters",
            len(resume_xml) if resume_xml else 0,
        )

        # Generate role recommendations using the LLM processor
        try:

            # Get role recommendations
            recommendations = generate_role_recommendations_from_xml(resume_xml)

            if not recommendations:
                logger.warning(
                    "No role recommendations generated for profile ID %s",
                    job_seeker_profile_id,
                )
                return {
                    "status": "error",
                    "message": "No suitable role recommendations could be generated",
                    "profile_id": job_seeker_profile_id,
                }

            # Save the recommendations to the database
            # First, delete any existing recommendations for this profile to avoid duplicates
            RoleRecommendation.objects.filter(job_seeker=profile).delete()

            # Save the recommendation objects
            created_recommendations = []
            for recommendation in recommendations:
                recommendation.job_seeker = profile  # Ensure job_seeker is set
                recommendation.save()
                created_recommendations.append(recommendation)

            # Log the successful creation
            logger.info(
                "Created %d role recommendations for %s",
                len(created_recommendations),
                profile.user_owner.email if profile.user_owner else "Unknown",
            )

            # Return success response with recommendations
            return {
                "status": "success",
                "message": "Role recommendations generated successfully",
                "profile_id": job_seeker_profile_id,
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

        except Exception as e:
            logger.error(
                "Error in LLM role recommendations generation: %s",
                str(e),
                exc_info=True,
            )
            return {
                "status": "error",
                "message": f"Error generating role recommendations: {str(e)}",
                "profile_id": job_seeker_profile_id,
            }

    except Exception as e:
        # Log the error
        logger.error("Error generating role recommendations: %s", str(e), exc_info=True)
        return {
            "status": "error",
            "message": f"Error generating role recommendations: {str(e)}",
            "profile_id": getattr(locals(), "job_seeker_profile_id", None),
        }
