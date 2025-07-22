"""URL patterns for the job_seekers app."""

from django.urls import path
from django.urls.resolvers import URLPattern

from apps.job_seekers.views.api_views import (
    TalentPoolStatusView,
    ToggleRoleInterestView,
    ToggleTalentPoolView,
)
from apps.job_seekers.views.dashboard_views import (
    DashboardView,
    RoleRecommendationsView,
    TalentSheetDetailsView,
)
from apps.job_seekers.views.job_opening_views import JobOpeningDetailView
from apps.job_seekers.views.job_seeker_profile_views import (
    ProfileView,
    ResumeView,
    SettingsView,
)
from apps.job_seekers.views.resume_processing_views import (
    ProfileCreateView,
    ResumeProcessingTaskProgressView,
    ResumeUploadView,
)
from apps.job_seekers.views.workshop_views import (
    ApplyUpgradedResumeView,
    DownloadUpgradedResumeView,
    TargetedDocsView,
    UpgradeResumeView,
    WorkshopLandingView,
)

app_name = "job_seekers"

urlpatterns: list[URLPattern] = [
    # Root of the job_seekers sub-site now redirects to the dashboard.
    path("", DashboardView.as_view(), name="dashboard"),
    path("dashboard/", DashboardView.as_view(), name="dashboard_alt"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/create/", ProfileCreateView.as_view(), name="profile_create"),
    path("settings/", SettingsView.as_view(), name="settings"),
    # Resume view for recruiters
    path("resume/<int:pk>/", ResumeView.as_view(), name="resume_view"),
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
    # Job opening detail (read-only) for job seekers
    path(
        "job-openings/<int:pk>/",
        JobOpeningDetailView.as_view(),
        name="job_opening_detail",
    ),
    # Workshop
    path("workshop/", WorkshopLandingView.as_view(), name="workshop"),
    path(
        "workshop/upgrade-resume/",
        UpgradeResumeView.as_view(),
        name="workshop_upgrade_resume",
    ),
    path(
        "workshop/upgrade-resume/download/",
        DownloadUpgradedResumeView.as_view(),
        name="workshop_upgrade_resume_download",
    ),
    path(
        "workshop/upgrade-resume/use/",
        ApplyUpgradedResumeView.as_view(),
        name="workshop_upgrade_resume_use",
    ),
    path(
        "workshop/targeted-docs/",
        TargetedDocsView.as_view(),
        name="workshop_targeted_docs",
    ),
    # API endpoints
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
