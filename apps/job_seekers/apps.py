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

    def ready(self) -> None:
        """
        Initialize signals when the app is ready.

        This imports the signals module to ensure signal handlers are registered.
        """
        # pylint: disable=import-outside-toplevel,unused-import
        import apps.job_seekers.signals  # noqa
