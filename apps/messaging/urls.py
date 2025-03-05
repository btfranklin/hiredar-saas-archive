"""
URL patterns for the messaging app.

This module defines the URL routes for messaging functionality,
including conversations, messages, and notifications.
"""

from django.urls import path

from apps.messaging.views.conversation_views import (ConversationDetailView,
                                                     ConversationListView,
                                                     SendMessageView,
                                                     StartConversationView)
from apps.messaging.views.notification_views import (
    MarkAllNotificationsReadView, MarkNotificationReadView,
    NotificationListView)

app_name = "messaging"

urlpatterns = [
    # Conversation URLs
    path("conversations/", ConversationListView.as_view(), name="conversations"),
    path(
        "conversations/<int:pk>/",
        ConversationDetailView.as_view(),
        name="conversation_detail",
    ),
    path(
        "conversations/create/<int:job_id>/<int:recipient_id>/",
        StartConversationView.as_view(),
        name="conversation_create",
    ),
    path(
        "conversations/<int:conversation_id>/send/",
        SendMessageView.as_view(),
        name="send_message",
    ),
    # Notification URLs
    path("notifications/", NotificationListView.as_view(), name="notifications"),
    path(
        "notifications/<int:pk>/mark-read/",
        MarkNotificationReadView.as_view(),
        name="mark_notification_read",
    ),
    path(
        "notifications/mark-all-read/",
        MarkAllNotificationsReadView.as_view(),
        name="mark_all_read",
    ),
]
