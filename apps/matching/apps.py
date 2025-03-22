"""
Configuration for the matching app.

This app manages candidate matching functionality for connecting job seekers to relevant job openings.
"""

from django.apps import AppConfig


class MatchingConfig(AppConfig):
    """Configuration for the matching app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.matching"
    verbose_name = "Matching"

    def ready(self):
        """
        Import signals when Django starts to ensure they're connected.
        """
        import apps.matching.signals  # noqa
