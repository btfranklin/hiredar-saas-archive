"""Matching app for Hiredar."""

# Re-export core matching functions for backward compatibility
from apps.matching.core import (
    average_vectors,
    get_job_section_embedding,
    get_talent_section_embedding,
    match_job_to_talents,
    match_talent_to_jobs,
    query_pinecone,
)

__all__ = [
    "average_vectors",
    "get_job_section_embedding",
    "get_talent_section_embedding",
    "match_job_to_talents",
    "match_talent_to_jobs",
    "query_pinecone",
]
