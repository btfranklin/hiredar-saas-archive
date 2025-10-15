"""Legacy configuration for the retired job_seekers app.

The runtime code now lives in ``apps.candidates``; this package remains so Django
can apply migrations that drop the old job seeker tables.
"""

from django.apps import AppConfig


class JobSeekersConfig(AppConfig):
    """AppConfig kept so Django can apply the remaining cleanup migrations."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.job_seekers"
    verbose_name = "Job Seekers"
