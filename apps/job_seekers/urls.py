"""URL patterns for the job_seekers app."""

from django.urls import path
from django.urls.resolvers import URLPattern

from apps.job_seekers.views import (
                                    DashboardView,
                                    ProfileCreateView,
                                    ProfileView,
                                    ResumeUploadView,
                                    SettingsView,
                                    TaskStatusView,
)

app_name = "job_seekers"

urlpatterns: list[URLPattern] = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/create/", ProfileCreateView.as_view(), name="profile_create"),
    path("settings/", SettingsView.as_view(), name="settings"),
    # Resume upload and processing
    path("resume-upload/", ResumeUploadView.as_view(), name="resume_upload"),
    path("task-status/<str:task_id>/", TaskStatusView.as_view(), name="task_status"),
]
