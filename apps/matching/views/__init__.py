"""
Views package for the matching app.

This package contains modules for different view-related functionality:

- candidate_views: Views for candidate matching and management.
"""

from apps.matching.views.candidate_views import (
    CandidateDetailView,
    CandidateMatchListView,
)

__all__ = ["CandidateDetailView", "CandidateMatchListView"]
