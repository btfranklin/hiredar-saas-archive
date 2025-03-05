"""
Authentication application configuration.

This module defines the Django application configuration for the authentication app,
which handles user authentication, registration, and user profile management.
"""

from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    """
    Configuration for the Authentication application.

    This class defines how Django interacts with the authentication app,
    including app name, auto field settings, and signals connection.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.authentication"
    verbose_name = "Authentication"

    def ready(self):
        """
        Initialize app when Django starts.

        Imports signals to ensure they are registered when the app is ready.
        """
        import apps.authentication.signals  # type: ignore # noqa
