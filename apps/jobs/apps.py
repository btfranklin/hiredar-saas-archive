"""
Configuration for the jobs app.

This app manages job listings, skills, candidate matching, and related functionality.
"""

from django.apps import AppConfig


class JobsConfig(AppConfig):
    """Configuration for the jobs app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.jobs"
    verbose_name = "Jobs"
