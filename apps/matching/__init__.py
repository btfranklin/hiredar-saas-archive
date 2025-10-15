"""Matching app for Hiredar."""

# Re-export core matching functions for backward compatibility
from apps.matching.core import (
    average_vectors,
    get_job_section_embedding,
    get_candidate_section_embedding,
    match_candidate_to_jobs,
    match_job_to_candidates,
    query_pinecone,
)

__all__ = [
    "average_vectors",
    "get_job_section_embedding",
    "get_candidate_section_embedding",
    "match_job_to_candidates",
    "match_candidate_to_jobs",
    "query_pinecone",
]
