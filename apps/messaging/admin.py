"""
Django admin configuration for the messaging app.

This module defines the admin interfaces for the messaging-related models,
providing configuration for how conversations, messages, and notifications
are displayed and managed in the Django admin interface.
"""

from django.contrib import admin

from .models import Conversation, Message, Notification


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """
    Admin configuration for Conversation model.

    Defines how conversations are displayed and managed in the Django admin,
    including display fields and search capabilities.
    """

    list_display = ("id", "created_at", "updated_at")
    search_fields = ("participants__email",)
    filter_horizontal = ("participants",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Admin configuration for Message model.

    Configures the admin interface for managing messages within conversations,
    including display fields, filters, and search functionality.
    """

    list_display = ("sender", "conversation", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("content", "sender__email")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Admin configuration for Notification model.

    Sets up the admin interface for user notifications,
    with appropriate display fields, filters, and search capabilities.
    """

    list_display = ("user", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("content", "user__email")
