"""
Core application configuration.

This module defines the Django application configuration for the core app,
which serves as the foundation for shared functionality across the platform.
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """
    Configuration for the Core application.

    This class defines how Django interacts with the core app,
    handling basic settings and application registration.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
