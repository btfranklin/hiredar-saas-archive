"""
Configuration for the job_seekers app.

This app manages job seeker profiles, skills, and related functionality.
"""

from django.apps import AppConfig


class JobSeekersConfig(AppConfig):
    """Configuration for the job_seekers app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.job_seekers"
    verbose_name = "Job Seekers"
