"""URL patterns for the job_seekers app."""

from django.urls import path
from django.urls.resolvers import URLPattern

from apps.job_seekers.views.api_views import (
    PersonalTaglineView,
    TalentPoolStatusView,
    ToggleRoleInterestView,
    ToggleTalentPoolView,
)
from apps.job_seekers.views.dashboard_views import (
    DashboardView,
    RoleRecommendationsView,
    TalentSheetDetailsView,
)
from apps.job_seekers.views.job_seeker_profile_views import ProfileView, SettingsView
from apps.job_seekers.views.resume_processing_views import (
    ProfileCreateView,
    ResumeProcessingTaskProgressView,
    ResumeUploadView,
)

app_name = "job_seekers"

urlpatterns: list[URLPattern] = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/create/", ProfileCreateView.as_view(), name="profile_create"),
    path("settings/", SettingsView.as_view(), name="settings"),
    # Recommendations
    path(
        "recommendations/",
        RoleRecommendationsView.as_view(),
        name="role_recommendations",
    ),
    # Talent sheet
    path(
        "talent-sheet/",
        TalentSheetDetailsView.as_view(),
        name="talent_sheet_details",
    ),
    # Resume upload and processing
    path("resume-upload/", ResumeUploadView.as_view(), name="resume_upload"),
    path(
        "task-status/<str:task_id>/",
        ResumeProcessingTaskProgressView.as_view(),
        name="task_status",
    ),
    # API endpoints
    path(
        "api/personal-tagline/",
        PersonalTaglineView.as_view(),
        name="api_personal_tagline",
    ),
    path(
        "api/toggle-role-interest/<int:role_id>/",
        ToggleRoleInterestView.as_view(),
        name="toggle_role_interest",
    ),
    path(
        "api/toggle-talent-pool/",
        ToggleTalentPoolView.as_view(),
        name="toggle_talent_pool",
    ),
    path(
        "api/talent-pool-status/",
        TalentPoolStatusView.as_view(),
        name="api_talent_pool_status",
    ),
]
