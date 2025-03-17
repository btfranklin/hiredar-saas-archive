"""
URL patterns for the jobs app.

This module defines the URL routes for job-related functionality,
including candidate matching and recommendations.
"""

from django.urls import path

from apps.jobs.views.candidate_views import (
    CandidateDetailView,
    CandidateMatchListView,
    toggle_shortlist,
)

app_name = "jobs"

urlpatterns = [
    # Candidate Matching
    path(
        "<int:job_id>/candidates/",
        CandidateMatchListView.as_view(),
        name="candidates",
    ),
    path(
        "<int:job_id>/candidates/<int:candidate_id>/",
        CandidateDetailView.as_view(),
        name="candidate_detail",
    ),
    path(
        "<int:job_id>/candidates/<int:candidate_id>/shortlist/",
        toggle_shortlist,
        name="toggle_shortlist",
    ),
]
