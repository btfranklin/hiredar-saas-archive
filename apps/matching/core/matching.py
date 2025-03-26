"""
Core matching algorithms.

This module contains the main algorithms for matching talent sheets and job openings.
"""

import logging
from typing import Any

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist

from apps.matching.core.pinecone_client import query_pinecone
from apps.matching.core.retrieval import (
    get_job_section_embedding,
    get_talent_section_embedding,
)
from apps.matching.core.vector_operations import average_vectors

logger = logging.getLogger(__name__)


def match_talent_to_jobs(
    talent_id: int, top_k: int = 10
) -> dict[str, list[dict[str, Any]]]:
    """
    Given a TalentSheet id, perform multiple matching queries against JobOpenings.
    Returns a dictionary with lists of job matches for different perspectives.

    Args:
        talent_id: ID of the TalentSheet to find matches for
        top_k: Number of results to return per perspective

    Returns:
        Dictionary with match results grouped by perspective
    """
    # Verify the TalentSheet exists
    try:
        talent_sheet = apps.get_model("job_seekers", "TalentSheet").objects.get(
            id=talent_id
        )
        if talent_sheet.status != "PUBLISHED":
            logger.warning(
                "TalentSheet %s is not published (status: %s)",
                talent_id,
                talent_sheet.status,
            )
    except ObjectDoesNotExist:
        logger.error("TalentSheet with id %s does not exist.", talent_id)
        return {
            "top_matches": [],
            "best_skills_fit": [],
            "experience_matches": [],
            "wildcard_matches": [],
        }

    # Retrieve embeddings for the talent's sections
    promotional = get_talent_section_embedding(talent_id, "Promotional Blurb")
    skills = get_talent_section_embedding(talent_id, "Skill Overview")
    ideal_roles = get_talent_section_embedding(talent_id, "Ideal Roles")

    if not promotional and not skills and not ideal_roles:
        logger.error("No embeddings found for talent_id: %s", talent_id)
        return {
            "top_matches": [],
            "best_skills_fit": [],
            "experience_matches": [],
            "wildcard_matches": [],
        }

    results = {}

    # --- Top Match (Holistic) ---
    # For a holistic view, we average available embeddings
    holistic_vectors = [
        vec for vec in (promotional, skills, ideal_roles) if vec is not None
    ]
    if holistic_vectors:
        holistic_query = average_vectors(holistic_vectors)
        top_matches = query_pinecone(
            query_vector=holistic_query, namespace="job_openings", top_k=top_k
        )
        results["top_matches"] = top_matches
    else:
        results["top_matches"] = []

    # --- Best Skills Fit ---
    if skills:
        skills_matches = query_pinecone(
            query_vector=skills,
            namespace="job_openings",
            top_k=top_k,
            filter_dict={"section": "Required Skills"},
        )
        results["best_skills_fit"] = skills_matches
    else:
        results["best_skills_fit"] = []

    # --- Most Relevant Experience ---
    if promotional:
        # Use Promotional Blurb to capture experience
        experience_matches = query_pinecone(
            query_vector=promotional,
            namespace="job_openings",
            top_k=top_k,
            filter_dict={"section": "Responsibilities"},
        )
        results["experience_matches"] = experience_matches
    else:
        results["experience_matches"] = []

    # --- Wildcard Matches ---
    if ideal_roles:
        wildcard_matches = query_pinecone(
            query_vector=ideal_roles,
            namespace="job_openings",
            top_k=top_k,
            filter_dict={"section": "Job Overview"},
        )
        results["wildcard_matches"] = wildcard_matches
    else:
        results["wildcard_matches"] = []

    return results


def match_job_to_talents(
    job_id: int, top_k: int = 10
) -> dict[str, list[dict[str, Any]]]:
    """
    Given a JobOpening id, perform matching queries against TalentSheets.
    Returns a dictionary with lists of candidate matches for different perspectives.

    Args:
        job_id: ID of the JobOpening to find matches for
        top_k: Number of results to return per perspective

    Returns:
        Dictionary with match results grouped by perspective
    """
    # Verify the JobOpening exists and is active
    try:
        job = apps.get_model("recruiters", "JobOpening").objects.get(id=job_id)
        if job.status != "active":
            logger.info(
                "Skipping match generation for inactive job %s: %s",
                job.id,
                job.title,
            )
            return {
                "top_matches": [],
                "best_skills_fit": [],
                "experience_matches": [],
                "wildcard_matches": [],
            }
    except ObjectDoesNotExist:
        logger.error("JobOpening with id %s does not exist.", job_id)
        return {
            "top_matches": [],
            "best_skills_fit": [],
            "experience_matches": [],
            "wildcard_matches": [],
        }

    # Retrieve job embeddings
    job_overview = get_job_section_embedding(job_id, "Job Overview")
    job_skills = get_job_section_embedding(job_id, "Required Skills")
    responsibilities = get_job_section_embedding(job_id, "Responsibilities")

    if not job_overview and not job_skills and not responsibilities:
        logger.error("No embeddings found for job_id: %s", job_id)
        return {
            "top_matches": [],
            "best_skills_fit": [],
            "experience_matches": [],
            "wildcard_matches": [],
        }

    results = {}

    # --- Top Match (Holistic) ---
    holistic_vectors = [
        vec for vec in (job_overview, job_skills, responsibilities) if vec is not None
    ]
    if holistic_vectors:
        holistic_query = average_vectors(holistic_vectors)
        top_matches = query_pinecone(
            query_vector=holistic_query, namespace="talent_sheets", top_k=top_k
        )
        results["top_matches"] = top_matches
    else:
        results["top_matches"] = []

    # --- Best Skills Fit ---
    if job_skills:
        skills_matches = query_pinecone(
            query_vector=job_skills,
            namespace="talent_sheets",
            top_k=top_k,
            filter_dict={"section": "Skill Overview"},
        )
        results["best_skills_fit"] = skills_matches
    else:
        results["best_skills_fit"] = []

    # --- Most Relevant Experience ---
    if responsibilities:
        experience_matches = query_pinecone(
            query_vector=responsibilities,
            namespace="talent_sheets",
            top_k=top_k,
            filter_dict={"section": "Promotional Blurb"},
        )
        results["experience_matches"] = experience_matches
    else:
        results["experience_matches"] = []

    # --- Wildcard Matches ---
    if job_overview:
        wildcard_matches = query_pinecone(
            query_vector=job_overview,
            namespace="talent_sheets",
            top_k=top_k,
            filter_dict={"section": "Ideal Roles"},
        )
        results["wildcard_matches"] = wildcard_matches
    else:
        results["wildcard_matches"] = []

    return results
