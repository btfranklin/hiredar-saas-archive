"""Views for the job_seekers app."""

from apps.job_seekers.views.dashboard_views import (
    DashboardView,
    RoleRecommendationsView,
)
from apps.job_seekers.views.job_seeker_profile_views import ProfileView, SettingsView
from apps.job_seekers.views.resume_processing_views import (
    ProfileCreateView,
    ResumeProcessingTaskProgressView,
    ResumeUploadView,
)

__all__ = [
    "DashboardView",
    "ProfileView",
    "ProfileCreateView",
    "ResumeUploadView",
    "ResumeProcessingTaskProgressView",
    "RoleRecommendationsView",
    "SettingsView",
]
