"""URL patterns for the job_seekers app."""

from django.urls import path
from django.urls.resolvers import URLPattern

from apps.job_seekers.views.job_seeker_profile_views import ResumeView

app_name = "job_seekers"

urlpatterns: list[URLPattern] = [
    path("resume/<int:pk>/", ResumeView.as_view(), name="resume_view"),
]
