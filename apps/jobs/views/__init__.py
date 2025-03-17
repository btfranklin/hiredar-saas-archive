"""
Views for the jobs app.

This module imports and exposes all views from the jobs app's view modules,
making them available for import directly from apps.jobs.views.
"""

from apps.jobs.views.candidate_views import (
    CandidateDetailView,
    CandidateMatchListView,
    toggle_shortlist,
)

# For backwards compatibility, expose all views at the module level
__all__ = [
    "CandidateMatchListView",
    "CandidateDetailView",
    "toggle_shortlist",
]
