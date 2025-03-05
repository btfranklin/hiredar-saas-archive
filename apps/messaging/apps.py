"""
Configuration for the messaging app.

This app manages conversations, messages, notifications, and related functionality.
"""

from django.apps import AppConfig


class MessagingConfig(AppConfig):
    """Configuration for the messaging app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.messaging"
    verbose_name = "Messaging"
