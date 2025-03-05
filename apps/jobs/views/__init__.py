"""
Views for the jobs app.

This module imports and exposes all views from the jobs app's view modules,
making them available for import directly from apps.jobs.views.
"""

from apps.jobs.views.candidate_views import (CandidateDetailView,
                                             CandidateMatchListView,
                                             toggle_shortlist)
from apps.jobs.views.job_views import (JobOpeningCreateView,
                                       JobOpeningDeleteView,
                                       JobOpeningDetailView,
                                       JobOpeningEditView, JobOpeningListView)
from apps.jobs.views.recommendation_views import RoleRecommendationsView

# For backwards compatibility, expose all views at the module level
__all__ = [
    "JobOpeningCreateView",
    "JobOpeningListView",
    "JobOpeningDetailView",
    "JobOpeningEditView",
    "JobOpeningDeleteView",
    "CandidateMatchListView",
    "CandidateDetailView",
    "toggle_shortlist",
    "RoleRecommendationsView",
]
