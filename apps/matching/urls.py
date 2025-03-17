"""
URL patterns for the matching app.

This module defines the URL routes for candidate matching functionality.
"""

from django.urls import path

from apps.matching.views.candidate_views import (
    CandidateDetailView,
    CandidateMatchListView,
    toggle_shortlist,
)

app_name = "matching"

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
