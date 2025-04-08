"""
Core matching algorithms.

This module contains the main algorithms for matching talent sheets and job openings.
"""

import logging
from typing import Any

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist

from .pinecone_client import query_pinecone
from .retrieval import get_job_section_embedding, get_talent_section_embedding
from .vector_operations import average_vectors

logger = logging.getLogger(__name__)

# Define section names for different parts of job openings and talent sheets
# Use exact format as stored in metadata (with proper capitalization and spaces)
JOB_OVERVIEW = "Job Overview"
JOB_REQUIRED_SKILLS = "Required Skills"
JOB_RESPONSIBILITIES = "Responsibilities"
JOB_QUALIFICATIONS = "Qualifications"
JOB_SOFT_SKILLS = "Soft Skills"

TALENT_SKILL_OVERVIEW = "Skill Overview"
TALENT_PROMO_BLURB = "Promotional Blurb"
TALENT_IDEAL_ROLES = "Ideal Roles"


def match_talent_to_jobs(
    talent_id: int, top_k: int = 10
) -> dict[str, list[dict[str, Any]]]:
    """Matches a talent sheet to job openings from multiple perspectives."""
    try:
        # Check if TalentSheet exists and is published before fetching embeddings
        talent_sheet = apps.get_model("job_seekers", "TalentSheet").objects.get(
            id=talent_id
        )
        if not talent_sheet.is_published:
            logger.warning("TalentSheet %s is not published.", talent_id)
            # Return empty structure if not published
            return {
                "holistic_matches": [],
                "skills_matches": [],
                "experience_matches": [],
                "wildcard_matches": [],
            }
    except ObjectDoesNotExist:
        logger.error("TalentSheet with id %s does not exist.", talent_id)
        return {
            "holistic_matches": [],
            "skills_matches": [],
            "experience_matches": [],
            "wildcard_matches": [],
        }

    # Fetch individual embeddings
    try:
        skills_embedding = get_talent_section_embedding(
            talent_id, TALENT_SKILL_OVERVIEW
        )
        promo_embedding = get_talent_section_embedding(talent_id, TALENT_PROMO_BLURB)
        ideal_roles_embedding = get_talent_section_embedding(
            talent_id, TALENT_IDEAL_ROLES
        )
    except Exception as e:
        logger.error(
            "Failed to retrieve one or more embeddings for talent %s: %s", talent_id, e
        )
        # Return empty results
        return {
            "holistic_matches": [],
            "skills_matches": [],
            "experience_matches": [],
            "wildcard_matches": [],
        }

    if not skills_embedding and not promo_embedding and not ideal_roles_embedding:
        logger.warning(
            "No embeddings found for talent %s. Cannot perform matching.", talent_id
        )
        return {
            "holistic_matches": [],
            "skills_matches": [],
            "experience_matches": [],
            "wildcard_matches": [],
        }

    # Initialize results structure
    results: dict[str, list[dict[str, Any]]] = {
        "holistic_matches": [],
        "skills_matches": [],
        "experience_matches": [],
        "wildcard_matches": [],
    }

    # 1. Holistic Match (Average talent vector vs all job vectors)
    try:
        holistic_vectors = [
            vec
            for vec in [skills_embedding, promo_embedding, ideal_roles_embedding]
            if vec is not None
        ]
        if holistic_vectors:
            holistic_query = average_vectors(holistic_vectors)
            holistic_matches = query_pinecone(
                query_vector=holistic_query, namespace="job_openings", top_k=top_k
            )
            results["holistic_matches"] = holistic_matches
        else:
            # This case should ideally not be reached due to the check above, but included for safety
            results["holistic_matches"] = []
            logger.warning(
                "Could not calculate holistic vector for talent %s", talent_id
            )
    except Exception as e:
        logger.error("Error during holistic match for talent %s: %s", talent_id, e)
        results["holistic_matches"] = []

    # 2. Skills Match (Talent Skill Overview vs Job Required Skills)
    try:
        if skills_embedding:
            skills_matches = query_pinecone(
                query_vector=skills_embedding,
                namespace="job_openings",
                top_k=top_k,
                filter_dict={"section": JOB_REQUIRED_SKILLS},
            )
            results["skills_matches"] = skills_matches
        else:
            results["skills_matches"] = []
    except Exception as e:
        logger.error("Error during skills match for talent %s: %s", talent_id, e)
        results["skills_matches"] = []

    # 3. Experience Match (Talent Promo Blurb vs Job Responsibilities)
    try:
        if promo_embedding:
            experience_matches = query_pinecone(
                query_vector=promo_embedding,
                namespace="job_openings",
                top_k=top_k,
                filter_dict={"section": JOB_RESPONSIBILITIES},
            )
            results["experience_matches"] = experience_matches
        else:
            results["experience_matches"] = []
    except Exception as e:
        logger.error("Error during experience match for talent %s: %s", talent_id, e)
        results["experience_matches"] = []

    # 4. Wildcard Match (Talent Ideal Roles vs Job Overview)
    try:
        if ideal_roles_embedding:
            wildcard_matches = query_pinecone(
                query_vector=ideal_roles_embedding,
                namespace="job_openings",
                top_k=top_k,
                filter_dict={"section": JOB_OVERVIEW},
            )
            results["wildcard_matches"] = wildcard_matches
        else:
            results["wildcard_matches"] = []
    except Exception as e:
        logger.error("Error during wildcard match for talent %s: %s", talent_id, e)
        results["wildcard_matches"] = []

    return results


def match_job_to_talents(
    job_id: int, top_k: int = 10
) -> dict[str, list[dict[str, Any]]]:
    """Matches a job opening to talent sheets from multiple perspectives."""
    try:
        # Check if JobOpening exists and is active before fetching embeddings
        job = apps.get_model("recruiters", "JobOpening").objects.get(id=job_id)
        if not job.is_active:
            logger.warning("JobOpening %s is not active.", job_id)
            # Return empty structure if not active
            return {
                "holistic_matches": [],
                "skills_matches": [],
                "experience_matches": [],
                "wildcard_matches": [],
            }
    except ObjectDoesNotExist:
        logger.error("JobOpening with id %s does not exist.", job_id)
        return {
            "holistic_matches": [],
            "skills_matches": [],
            "experience_matches": [],
            "wildcard_matches": [],
        }

    # Fetch individual embeddings
    try:
        overview_embedding = get_job_section_embedding(job_id, JOB_OVERVIEW)
        skills_embedding = get_job_section_embedding(job_id, JOB_REQUIRED_SKILLS)
        resp_embedding = get_job_section_embedding(job_id, JOB_RESPONSIBILITIES)
    except Exception as e:
        logger.error(
            "Failed to retrieve one or more embeddings for job %s: %s", job_id, e
        )
        # Decide if partial matching is okay or return empty
        return {
            "holistic_matches": [],
            "skills_matches": [],
            "experience_matches": [],
            "wildcard_matches": [],
        }

    if not overview_embedding and not skills_embedding and not resp_embedding:
        logger.warning(
            "No embeddings found for job %s. Cannot perform matching.", job_id
        )
        return {
            "holistic_matches": [],
            "skills_matches": [],
            "experience_matches": [],
            "wildcard_matches": [],
        }

    # Initialize results structure
    results: dict[str, list[dict[str, Any]]] = {
        "holistic_matches": [],
        "skills_matches": [],
        "experience_matches": [],
        "wildcard_matches": [],
    }

    # 1. Holistic Match (Average job vector vs all talent vectors)
    try:
        holistic_vectors = [
            vec
            for vec in [overview_embedding, skills_embedding, resp_embedding]
            if vec is not None
        ]
        if holistic_vectors:
            holistic_query = average_vectors(holistic_vectors)
            holistic_matches = query_pinecone(
                query_vector=holistic_query, namespace="talent_sheets", top_k=top_k
            )
            results["holistic_matches"] = holistic_matches
        else:
            # This case should ideally not be reached
            results["holistic_matches"] = []
            logger.warning("Could not calculate holistic vector for job %s", job_id)
    except Exception as e:
        logger.error("Error during holistic match for job %s: %s", job_id, e)
        results["holistic_matches"] = []

    # 2. Skills Match (Job Required Skills vs Talent Skill Overview)
    try:
        if skills_embedding:
            skills_matches = query_pinecone(
                query_vector=skills_embedding,
                namespace="talent_sheets",
                top_k=top_k,
                filter_dict={"section": TALENT_SKILL_OVERVIEW},
            )
            results["skills_matches"] = skills_matches
        else:
            results["skills_matches"] = []
    except Exception as e:
        logger.error("Error during skills match for job %s: %s", job_id, e)
        results["skills_matches"] = []

    # 3. Experience Match (Job Responsibilities vs Talent Promo Blurb)
    try:
        if resp_embedding:
            experience_matches = query_pinecone(
                query_vector=resp_embedding,
                namespace="talent_sheets",
                top_k=top_k,
                filter_dict={"section": TALENT_PROMO_BLURB},
            )
            results["experience_matches"] = experience_matches
        else:
            results["experience_matches"] = []
    except Exception as e:
        logger.error("Error during experience match for job %s: %s", job_id, e)
        results["experience_matches"] = []

    # 4. Wildcard Match (Job Overview vs Talent Ideal Roles)
    try:
        if overview_embedding:
            wildcard_matches = query_pinecone(
                query_vector=overview_embedding,
                namespace="talent_sheets",
                top_k=top_k,
                filter_dict={"section": TALENT_IDEAL_ROLES},
            )
            results["wildcard_matches"] = wildcard_matches
        else:
            results["wildcard_matches"] = []
    except Exception as e:
        logger.error("Error during wildcard match for job %s: %s", job_id, e)
        results["wildcard_matches"] = []

    return results
