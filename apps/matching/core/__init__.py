"""
Core matching functionality.

This package contains the core components for vector-based matching between
talent sheets and job openings.
"""

from apps.matching.core.matching import match_job_to_talents, match_talent_to_jobs
from apps.matching.core.pinecone_client import query_pinecone
from apps.matching.core.retrieval import (
    get_job_section_embedding,
    get_talent_section_embedding,
)

# Re-export main functions for backward compatibility
from apps.matching.core.vector_operations import average_vectors

__all__ = [
    "average_vectors",
    "query_pinecone",
    "get_talent_section_embedding",
    "get_job_section_embedding",
    "match_talent_to_jobs",
    "match_job_to_talents",
]
