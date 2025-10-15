"""
Task functions for the matching app.

This package contains task functions for embedding and matching functionality.
"""

# Re-export standalone task modules for embedding and matching functionality
from apps.matching.tasks.analyze_candidate_match import analyze_candidate_match
from apps.matching.tasks.create_candidate_matches import create_candidate_matches
from apps.matching.tasks.create_job_opening_embeddings import (
    create_job_opening_embeddings,
)
from apps.matching.tasks.create_candidate_embeddings import create_candidate_embeddings
from apps.matching.tasks.match_candidate_to_active_jobs import match_candidate_to_active_jobs
from apps.matching.tasks.remove_job_opening_embeddings import (
    remove_job_opening_embeddings,
)
from apps.matching.tasks.remove_job_opening_matches import remove_job_opening_matches
from apps.matching.tasks.remove_candidate_embeddings import remove_candidate_embeddings
from apps.matching.tasks.remove_candidate_matches import remove_candidate_matches

__all__ = [
    "analyze_candidate_match",
    "create_job_opening_embeddings",
    "remove_job_opening_embeddings",
    "create_candidate_embeddings",
    "remove_candidate_embeddings",
    "create_candidate_matches",
    "remove_job_opening_matches",
    "match_candidate_to_active_jobs",
    "remove_candidate_matches",
]
