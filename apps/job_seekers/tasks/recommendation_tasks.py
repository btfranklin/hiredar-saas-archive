"""
Recommendation tasks for job seekers.

This module contains Django Q2 tasks for generating role recommendations,
personal taglines, and other AI-generated recommendations for job seekers.
"""

import logging
from typing import Any

from apps.job_seekers.models import JobSeekerProfile, RoleRecommendation
from apps.job_seekers.utils.recommendation.llm_processor import (
    generate_personal_tagline as generate_tagline_from_xml,
)
from apps.job_seekers.utils.recommendation.llm_processor import (
    generate_role_recommendations as generate_role_recommendations_from_xml,
)

# Setup logging
logger = logging.getLogger(__name__)


def generate_role_recommendations(job_seeker_profile_id: int) -> dict[str, Any]:
    """
    Generate role recommendations for a job seeker based on their profile.

    This task analyzes the job seeker's skills, experience, and other profile
    data to generate career role recommendations.

    Args:
        job_seeker_profile_id: ID of the JobSeekerProfile to generate recommendations for

    Returns:
        dict: Result of the recommendation operation
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
        logger.info(
            "Generating role recommendations for job seeker: %s",
            profile.user_owner.email,
        )

        # Check if we have resume XML data
        if not profile.resume_xml:
            logger.warning(
                "No resume XML data available for profile ID %s", job_seeker_profile_id
            )
            return {
                "success": False,
                "message": "Cannot generate role recommendations: No resume data available",
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
                    "success": False,
                    "message": "No suitable role recommendations could be generated",
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
                profile.user_owner.email,
            )

            # Return success response with recommendations
            return {
                "success": True,
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
                "success": False,
                "message": f"Error generating role recommendations: {str(e)}",
            }

    except Exception as e:
        # Log the error
        logger.error("Error generating role recommendations: %s", str(e), exc_info=True)
        return {
            "success": False,
            "message": f"Error generating role recommendations: {str(e)}",
        }


def generate_personal_tagline(job_seeker_profile_id: int) -> dict[str, Any]:
    """
    Generate a personal tagline for a job seeker based on their profile.

    This task creates a concise, professional tagline that highlights the
    job seeker's key strengths, skills, and career focus.

    Args:
        job_seeker_profile_id: ID of the JobSeekerProfile to generate a tagline for

    Returns:
        dict: Result of the tagline generation operation
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
        logger.info(
            "Generating personal tagline for job seeker: %s", profile.user_owner.email
        )

        # Check if we have resume XML data
        if not profile.resume_xml:
            logger.warning(
                "No resume XML data available for profile ID %s", job_seeker_profile_id
            )
            return {
                "success": False,
                "message": "Cannot generate tagline: No resume data available",
            }

        # Validate XML content
        resume_xml = profile.resume_xml
        logger.info(
            "Resume XML found, length: %d characters",
            len(resume_xml) if resume_xml else 0,
        )

        # Generate the tagline using the LLM processor
        try:
            tagline = generate_tagline_from_xml(resume_xml)

            # Save the tagline to the user's profile
            profile.personal_tagline = tagline
            profile.save(update_fields=["personal_tagline"])

            logger.info(
                "Generated tagline for %s: %s", profile.user_owner.email, tagline
            )

            return {
                "success": True,
                "message": "Personal tagline generated successfully",
                "profile_id": job_seeker_profile_id,
                "tagline": tagline,
            }

        except Exception as e:
            logger.error("Error in LLM tagline generation: %s", str(e), exc_info=True)
            return {
                "success": False,
                "message": f"Error generating tagline: {str(e)}",
            }

    except Exception as e:
        # Log the error
        logger.error("Error generating personal tagline: %s", str(e), exc_info=True)
        return {
            "success": False,
            "message": f"Error generating personal tagline: {str(e)}",
        }
