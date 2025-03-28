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
        # Only register the middleware in non-testing environments
        from django.conf import settings

        import apps.job_seekers.signals  # noqa

        if hasattr(settings, "MIDDLEWARE") and not getattr(settings, "TESTING", False):
            # Register our middleware by adding it to settings.MIDDLEWARE if not already there
            middleware_path = "apps.job_seekers.middleware.CleanupSchedulerMiddleware"
            if middleware_path not in settings.MIDDLEWARE:
                # Add to the beginning of middleware list to run early
                settings.MIDDLEWARE = [middleware_path] + list(settings.MIDDLEWARE)
