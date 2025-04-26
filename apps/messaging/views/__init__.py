"""
Messaging views module.

This package re-exports all views from the modular messaging views structure.
"""

from .conversation_views import (
    ConversationDetailView,
    ConversationListView,
    RespondToInterestView,
    SendMessageView,
    StartConversationView,
)
from .notification_views import (
    MarkAllNotificationsReadView,
    MarkNotificationReadView,
    NotificationListView,
)

# For backwards compatibility, expose all views at the module level
__all__ = [
    "ConversationListView",
    "ConversationDetailView",
    "StartConversationView",
    "SendMessageView",
    "RespondToInterestView",
    "NotificationListView",
    "MarkNotificationReadView",
    "MarkAllNotificationsReadView",
]
