"""URL patterns for the job_seekers app."""

from django.urls import path
from django.urls.resolvers import URLPattern

from apps.job_seekers.views.dashboard_views import DashboardView
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
    # Resume upload and processing
    path("resume-upload/", ResumeUploadView.as_view(), name="resume_upload"),
    path(
        "task-status/<str:task_id>/",
        ResumeProcessingTaskProgressView.as_view(),
        name="task_status",
    ),
]
