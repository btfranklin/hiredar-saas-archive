"""
Core matching functionality.

This package contains the core components for vector-based matching between
candidate profiles and job openings.
"""

from apps.matching.core.matching import match_candidate_to_jobs, match_job_to_candidates
from apps.matching.core.pinecone_client import query_pinecone
from apps.matching.core.retrieval import (
    get_job_section_embedding,
    get_candidate_section_embedding,
)

# Re-export main functions for backward compatibility
from apps.matching.core.vector_operations import average_vectors

__all__ = [
    "average_vectors",
    "query_pinecone",
    "get_candidate_section_embedding",
    "get_job_section_embedding",
    "match_candidate_to_jobs",
    "match_job_to_candidates",
]
