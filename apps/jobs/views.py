"""
Jobs views module.

This module re-exports all views from the modular jobs views structure.
For backwards compatibility, all views are available at the module level.
"""

from apps.jobs.views.candidate_views import (CandidateDetailView,
                                             CandidateMatchListView,
                                             toggle_shortlist)
# Import all views from the modular structure
from apps.jobs.views.job_views import (JobOpeningCreateView,
                                       JobOpeningDeleteView,
                                       JobOpeningDetailView,
                                       JobOpeningEditView, JobOpeningListView)

# For backwards compatibility, keep all views at the module level
__all__ = [
    "JobOpeningCreateView",
    "JobOpeningListView",
    "JobOpeningDetailView",
    "JobOpeningEditView",
    "JobOpeningDeleteView",
    "CandidateMatchListView",
    "CandidateDetailView",
    "toggle_shortlist",
]
