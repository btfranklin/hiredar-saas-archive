"""
URL patterns for the matching app.

This module defines the URL routes for candidate matching functionality.
"""

from django.urls import path

from apps.matching.views.candidate_views import CandidateDetailView, withdraw_interest
from apps.matching.views.matching_views import match_job_api, match_talent_api

app_name = "matching"

urlpatterns = [
    # Candidate Matching
    path(
        "<int:job_id>/candidates/<int:candidate_id>/",
        CandidateDetailView.as_view(),
        name="candidate_match_detail",
    ),
    path(
        "<int:job_id>/candidates/<int:candidate_id>/withdraw-interest/",
        withdraw_interest,
        name="withdraw_interest",
    ),
    # Matching API endpoints
    path(
        "api/match/talent/<int:talent_id>/",
        match_talent_api,
        name="match_talent_api",
    ),
    path(
        "api/match/job/<int:job_id>/",
        match_job_api,
        name="match_job_api",
    ),
]
