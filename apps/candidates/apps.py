"""
Configuration for the candidates app.

This app manages recruiter-owned candidate records shared across the platform.
"""

from django.apps import AppConfig


class CandidatesConfig(AppConfig):
    """Application configuration for the candidates app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.candidates"
    verbose_name = "Candidates"

