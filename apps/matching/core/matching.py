"""
Core matching algorithms.

This module contains the main algorithms for matching candidate profiles and job openings.
"""

import logging
from typing import Any

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist

from .pinecone_client import query_pinecone
from .retrieval import get_job_section_embedding, get_candidate_section_embedding
from .vector_operations import average_vectors

logger = logging.getLogger(__name__)

# Define section names for different parts of job openings and candidate profiles
# Use exact format as stored in metadata (with proper capitalization and spaces)
JOB_OVERVIEW = "Job Overview"
JOB_REQUIRED_SKILLS = "Required Skills"
JOB_RESPONSIBILITIES = "Responsibilities"
JOB_QUALIFICATIONS = "Qualifications"
JOB_SOFT_SKILLS = "Soft Skills"

TALENT_EXPERIENCE_OVERVIEW = "Experience Overview"
TALENT_CAREER_DIRECTION = "Career Direction"
TALENT_SKILLS = "Skills"
TALENT_QUALIFICATIONS = "Qualifications"


def match_candidate_to_jobs(
    candidate_id: int, top_k: int = 10
) -> dict[str, list[dict[str, Any]]]:
    """Matches a candidate profile to job openings from multiple perspectives."""
    try:
        candidate_profile = apps.get_model("candidates", "CandidateProfile").objects.get(
            id=candidate_id
        )
        if not candidate_profile.is_published:
            logger.warning("CandidateProfile %s is not published.", candidate_id)
            return {
                "holistic_matches": [],
                "skills_matches": [],
                "experience_matches": [],
                "wildcard_matches": [],
                "qualifications_matches": [],
            }
    except ObjectDoesNotExist:
        logger.error("CandidateProfile with id %s does not exist.", candidate_id)
        return {
            "holistic_matches": [],
            "skills_matches": [],
            "experience_matches": [],
            "wildcard_matches": [],
            "qualifications_matches": [],
        }

    try:
        skills_embedding = get_candidate_section_embedding(candidate_id, TALENT_SKILLS)
        if skills_embedding is None:
            skills_embedding = get_candidate_section_embedding(
                candidate_id, TALENT_EXPERIENCE_OVERVIEW
            )

        experience_embedding = get_candidate_section_embedding(
            candidate_id, TALENT_EXPERIENCE_OVERVIEW
        )

        career_direction_embedding = get_candidate_section_embedding(
            candidate_id, TALENT_CAREER_DIRECTION
        )

        qualifications_embedding = get_candidate_section_embedding(
            candidate_id, TALENT_QUALIFICATIONS
        )
    except Exception as e:
        logger.error(
            "Failed to retrieve one or more embeddings for candidate %s: %s",
            candidate_id,
            e,
        )
        return {
            "holistic_matches": [],
            "skills_matches": [],
            "experience_matches": [],
            "wildcard_matches": [],
            "qualifications_matches": [],
        }

    if (
        not skills_embedding
        and not experience_embedding
        and not career_direction_embedding
        and not qualifications_embedding
    ):
        logger.warning(
            "No embeddings found for candidate %s. Cannot perform matching.",
            candidate_id,
            )
        return {
            "holistic_matches": [],
            "skills_matches": [],
            "experience_matches": [],
            "wildcard_matches": [],
            "qualifications_matches": [],
        }

    results: dict[str, list[dict[str, Any]]] = {
        "holistic_matches": [],
        "skills_matches": [],
        "experience_matches": [],
        "wildcard_matches": [],
        "qualifications_matches": [],
    }

    try:
        holistic_vectors = [
            vec
            for vec in [
                skills_embedding,
                experience_embedding,
                career_direction_embedding,
                qualifications_embedding,
            ]
            if vec is not None
        ]
        if holistic_vectors:
            holistic_query = average_vectors(holistic_vectors)
            holistic_matches = query_pinecone(
                query_vector=holistic_query, namespace="job_openings", top_k=top_k
            )
            results["holistic_matches"] = holistic_matches
        else:
            results["holistic_matches"] = []
            logger.warning(
                "Could not calculate holistic vector for candidate %s", candidate_id
            )
    except Exception as e:
        logger.error(
            "Error during holistic match for candidate %s: %s", candidate_id, e
        )
        results["holistic_matches"] = []

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
        logger.error(
            "Error during skills match for candidate %s: %s", candidate_id, e
        )
        results["skills_matches"] = []

    try:
        if experience_embedding:
            experience_matches = query_pinecone(
                query_vector=experience_embedding,
                namespace="job_openings",
                top_k=top_k,
                filter_dict={"section": JOB_RESPONSIBILITIES},
            )
            results["experience_matches"] = experience_matches
        else:
            results["experience_matches"] = []
    except Exception as e:
        logger.error(
            "Error during experience match for candidate %s: %s", candidate_id, e
        )
        results["experience_matches"] = []

    try:
        if career_direction_embedding:
            wildcard_matches = query_pinecone(
                query_vector=career_direction_embedding,
                namespace="job_openings",
                top_k=top_k,
                filter_dict={"section": JOB_OVERVIEW},
            )
            results["wildcard_matches"] = wildcard_matches
        else:
            results["wildcard_matches"] = []
    except Exception as e:
        logger.error(
            "Error during wildcard match for candidate %s: %s", candidate_id, e
        )
        results["wildcard_matches"] = []

    try:
        if qualifications_embedding:
            qualifications_matches = query_pinecone(
                query_vector=qualifications_embedding,
                namespace="job_openings",
                top_k=top_k,
                filter_dict={"section": JOB_QUALIFICATIONS},
            )
            results["qualifications_matches"] = qualifications_matches
        else:
            results["qualifications_matches"] = []
    except Exception as e:
        logger.error(
            "Error during qualifications match for candidate %s: %s",
            candidate_id,
            e,
        )
        results["qualifications_matches"] = []

    return results


def match_job_to_candidates(
    job_id: int, top_k: int = 10
) -> dict[str, list[dict[str, Any]]]:
    """Matches a job opening to candidate profiles from multiple perspectives."""
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
                "qualifications_matches": [],
            }
    except ObjectDoesNotExist:
        logger.error("JobOpening with id %s does not exist.", job_id)
        return {
            "holistic_matches": [],
            "skills_matches": [],
            "experience_matches": [],
            "wildcard_matches": [],
            "qualifications_matches": [],
        }

    # Fetch individual embeddings
    try:
        overview_embedding = get_job_section_embedding(job_id, JOB_OVERVIEW)
        skills_embedding = get_job_section_embedding(job_id, JOB_REQUIRED_SKILLS)
        resp_embedding = get_job_section_embedding(job_id, JOB_RESPONSIBILITIES)
        qualifications_embedding = get_job_section_embedding(job_id, JOB_QUALIFICATIONS)
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
            "qualifications_matches": [],
        }

    if (
        not overview_embedding
        and not skills_embedding
        and not resp_embedding
        and not qualifications_embedding
    ):
        logger.warning(
            "No embeddings found for job %s. Cannot perform matching.", job_id
        )
        return {
            "holistic_matches": [],
            "skills_matches": [],
            "experience_matches": [],
            "wildcard_matches": [],
            "qualifications_matches": [],
        }

    # Initialize results structure
    results: dict[str, list[dict[str, Any]]] = {
        "holistic_matches": [],
        "skills_matches": [],
        "experience_matches": [],
        "wildcard_matches": [],
        "qualifications_matches": [],
    }

    # 1. Holistic Match (Average job vector vs all candidate vectors)
    try:
        holistic_vectors = [
            vec
            for vec in [
                overview_embedding,
                skills_embedding,
                resp_embedding,
                qualifications_embedding,
            ]
            if vec is not None
        ]
        if holistic_vectors:
            holistic_query = average_vectors(holistic_vectors)
            holistic_matches = query_pinecone(
                query_vector=holistic_query,
                namespace="candidate_profiles",
                top_k=top_k,
            )
            results["holistic_matches"] = holistic_matches
        else:
            # This case should ideally not be reached
            results["holistic_matches"] = []
            logger.warning("Could not calculate holistic vector for job %s", job_id)
    except Exception as e:
        logger.error("Error during holistic match for job %s: %s", job_id, e)
        results["holistic_matches"] = []

    # 2. Skills Match (Job Required Skills vs Candidate Skills)
    try:
        if skills_embedding:
            skills_matches = query_pinecone(
                query_vector=skills_embedding,
                namespace="candidate_profiles",
                top_k=top_k,
                filter_dict={"section": TALENT_SKILLS},
            )
            # Fallback to Experience Overview in case Skills section is missing
            if not skills_matches:
                skills_matches = query_pinecone(
                    query_vector=skills_embedding,
                    namespace="candidate_profiles",
                    top_k=top_k,
                    filter_dict={"section": TALENT_EXPERIENCE_OVERVIEW},
                )
            results["skills_matches"] = skills_matches
        else:
            results["skills_matches"] = []
    except Exception as e:
        logger.error("Error during skills match for job %s: %s", job_id, e)
        results["skills_matches"] = []

    # 3. Relevant Experience Match (Job Responsibilities vs Candidate Experience Overview)
    try:
        if resp_embedding:
            experience_matches = query_pinecone(
                query_vector=resp_embedding,
                namespace="candidate_profiles",
                top_k=top_k,
                filter_dict={"section": TALENT_EXPERIENCE_OVERVIEW},
            )
            results["experience_matches"] = experience_matches
        else:
            results["experience_matches"] = []
    except Exception as e:
        logger.error("Error during experience match for job %s: %s", job_id, e)
        results["experience_matches"] = []

    # 4. Wildcard Match (Job Overview vs Candidate Career Direction)
    try:
        if overview_embedding:
            wildcard_matches = query_pinecone(
                query_vector=overview_embedding,
                namespace="candidate_profiles",
                top_k=top_k,
                filter_dict={"section": TALENT_CAREER_DIRECTION},
            )
            results["wildcard_matches"] = wildcard_matches
        else:
            results["wildcard_matches"] = []
    except Exception as e:
        logger.error("Error during wildcard match for job %s: %s", job_id, e)
        results["wildcard_matches"] = []

    # 5. Qualifications Match (Job Qualifications vs Candidate Qualifications)
    try:
        if qualifications_embedding:
            qualifications_matches = query_pinecone(
                query_vector=qualifications_embedding,
                namespace="candidate_profiles",
                top_k=top_k,
                filter_dict={"section": TALENT_QUALIFICATIONS},
            )
            results["qualifications_matches"] = qualifications_matches
        else:
            results["qualifications_matches"] = []
    except Exception as e:
        logger.error("Error during qualifications match for job %s: %s", job_id, e)
        results["qualifications_matches"] = []

    return results
