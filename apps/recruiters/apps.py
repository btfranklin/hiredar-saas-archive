"""
Configuration for the recruiters app.

This app manages recruiter profiles, companies, and related functionality.
"""

from django.apps import AppConfig


class RecruitersConfig(AppConfig):
    """Configuration for the recruiters app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.recruiters"
    verbose_name = "Recruiters"

    def ready(self) -> None:
        """
        Initialize signals when the app is ready.

        This imports the signals module to ensure signal handlers are registered.
        """
        # pylint: disable=import-outside-toplevel,unused-import
        import apps.recruiters.signals  # noqa
