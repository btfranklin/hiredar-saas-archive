"""
Matching functionality for comparing talent sheets and job openings.

This module implements vector-based matching between talent sheets and job openings
using multiple perspectives (holistic, skills, experience, etc.).
"""

import logging
from typing import Any

import numpy as np
from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist

from apps.matching.tasks.common import get_index

logger = logging.getLogger(__name__)


def average_vectors(vectors: list[list[float]]) -> list[float]:
    """
    Utility to compute the average vector from a list of vectors.

    Args:
        vectors: List of embedding vectors to average

    Returns:
        The averaged vector
    """
    if not vectors:
        raise ValueError("Cannot average an empty list of vectors")
    return np.mean(np.array(vectors), axis=0).tolist()


def query_pinecone(
    query_vector: list[float],
    namespace: str,
    top_k: int = 10,
    filter_dict: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Query Pinecone with the provided vector.

    Args:
        query_vector: The embedding vector to use as query
        namespace: The Pinecone namespace to query ('job_openings' or 'talent_sheets')
        top_k: Number of results to return
        filter_dict: Optional metadata filter to apply

    Returns:
        List of matches with metadata and scores
    """
    try:
        # Get the Pinecone index
        index = get_index()

        # Execute the query
        query_response = index.query(
            namespace=namespace,
            top_k=top_k,
            include_metadata=True,
            vector=query_vector,
            filter=filter_dict,
        )
        # The response structure depends on the Pinecone client version
        # For the gRPC client, matches are a property of the response
        return getattr(query_response, "matches", [])
    except Exception as e:
        logger.error("Error querying Pinecone: %s", e)
        return []


def get_talent_section_embedding(talent_id: int, section: str) -> list[float] | None:
    """
    Retrieve the embedding for a specific section of a talent sheet.

    Args:
        talent_id: ID of the talent sheet
        section: Section name (e.g., 'promotional_blurb', 'skill_overview')

    Returns:
        The embedding vector or None if not found
    """
    try:
        # Get the Pinecone index
        index = get_index()

        vector_id = f"talent_{talent_id}_{section}"
        result = index.fetch(ids=[vector_id], namespace="talent_sheets")

        if not result.vectors:
            logger.warning(
                "Vector %s not found in Pinecone namespace 'talent_sheets'.", vector_id
            )
            return None

        return result.vectors[vector_id].values
    except Exception as e:
        logger.error("Error fetching talent embedding: %s", e)
        return None


def get_job_section_embedding(job_id: int, section: str) -> list[float] | None:
    """
    Retrieve the embedding for a specific section of a job opening.

    Args:
        job_id: ID of the job opening
        section: Section name (e.g., 'job_overview', 'required_skills')

    Returns:
        The embedding vector or None if not found
    """
    try:
        # Get the Pinecone index
        index = get_index()

        vector_id = f"job_{job_id}_{section}"
        result = index.fetch(ids=[vector_id], namespace="job_openings")

        if not result.vectors:
            logger.warning(
                "Vector %s not found in Pinecone namespace 'job_openings'.", vector_id
            )
            return None

        return result.vectors[vector_id].values
    except Exception as e:
        logger.error("Error fetching job embedding: %s", e)
        return None


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
