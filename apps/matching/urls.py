"""
URL patterns for the matching app.

This module defines the URL routes for candidate matching functionality.
"""

from django.urls import path

from apps.matching.views.candidate_views import (
    CandidateDetailView,
    add_to_shortlist,
    candidate_match_analysis_status,
    remove_from_shortlist,
)
from apps.matching.views.matching_views import match_candidate_api, match_job_api

app_name = "matching"

urlpatterns = [
    # Candidate Matching
    path(
        "<int:job_id>/candidates/<int:candidate_id>/",
        CandidateDetailView.as_view(),
        name="candidate_match_detail",
    ),
    path(
        "<int:job_id>/candidates/<int:candidate_id>/analysis-status/",
        candidate_match_analysis_status,
        name="candidate_match_analysis_status",
    ),
    path(
        "<int:job_id>/candidates/<int:candidate_id>/shortlist/",
        add_to_shortlist,
        name="add_to_shortlist",
    ),
    path(
        "<int:job_id>/shortlist/<int:shortlist_id>/remove/",
        remove_from_shortlist,
        name="remove_from_shortlist",
    ),
    # Matching API endpoints
    path(
        "api/match/candidate/<int:candidate_id>/",
        match_candidate_api,
        name="match_candidate_api",
    ),
    path(
        "api/match/job/<int:job_id>/",
        match_job_api,
        name="match_job_api",
    ),
]
