"""
URL patterns for the jobs app.

This module defines the URL routes for job-related functionality,
including job openings, candidate matching, and role recommendations.
"""

from django.urls import path

from apps.jobs.views.candidate_views import (CandidateDetailView,
                                             CandidateMatchListView,
                                             toggle_shortlist)
from apps.jobs.views.job_views import (JobOpeningCreateView,
                                       JobOpeningDeleteView,
                                       JobOpeningDetailView,
                                       JobOpeningEditView, JobOpeningListView)
from apps.jobs.views.recommendation_views import RoleRecommendationsView

app_name = "jobs"

urlpatterns = [
    # Job Opening CRUD
    path("create/", JobOpeningCreateView.as_view(), name="create"),
    path("list/", JobOpeningListView.as_view(), name="list"),
    path("<int:pk>/", JobOpeningDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", JobOpeningEditView.as_view(), name="edit"),
    path("<int:pk>/delete/", JobOpeningDeleteView.as_view(), name="delete"),
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
    # Role Recommendations
    path(
        "recommendations/",
        RoleRecommendationsView.as_view(),
        name="recommendations",
    ),
]
