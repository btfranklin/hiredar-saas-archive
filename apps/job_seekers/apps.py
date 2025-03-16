"""
Configuration for the job_seekers app.

This app manages job seeker profiles, skills, and related functionality.
"""

import logging

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
        # Register the cleanup schedule in a way that doesn't query the database during startup
        from django.core.signals import request_started
        from django.dispatch import receiver

        import apps.job_seekers.signals  # noqa

        @receiver(request_started, weak=False)
        def ensure_cleanup_task_scheduled(sender, **kwargs):
            try:
                # Only run once per process
                if not getattr(ensure_cleanup_task_scheduled, "has_run", False):
                    ensure_cleanup_task_scheduled.has_run = True

                    # Schedule the task using the task module to avoid circular imports
                    from apps.job_seekers.tasks import ensure_cleanup_scheduled

                    ensure_cleanup_scheduled()
                    logging.getLogger(__name__).info(
                        "Cleanup task scheduled, ensured by %s", sender
                    )
            except Exception as e:
                # Log the error but don't crash the app startup
                logging.getLogger(__name__).error(
                    "Error scheduling cleanup task: %s", e
                )
