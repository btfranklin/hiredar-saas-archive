"""URL patterns for the candidates app."""

from django.urls import path

from apps.candidates.views import ResumeView

app_name = "candidates"

urlpatterns = [
    path("<int:pk>/resume/", ResumeView.as_view(), name="resume_view"),
]

