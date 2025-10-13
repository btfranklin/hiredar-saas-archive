"""Django app configuration for the reports module."""

from django.apps import AppConfig


class ReportsConfig(AppConfig):
    """Configure the reports Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reports"
