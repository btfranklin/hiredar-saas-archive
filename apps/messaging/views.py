"""
Messaging views module.

This module re-exports all views from the modular messaging views structure.
For backwards compatibility, all views are available at the module level.
"""

# Import all views from the modular structure
from apps.messaging.views.conversation_views import (ConversationDetailView,
                                                     ConversationListView,
                                                     SendMessageView,
                                                     StartConversationView)
from apps.messaging.views.notification_views import (
    MarkAllNotificationsReadView, MarkNotificationReadView,
    NotificationListView)

# For backwards compatibility, keep all views at the module level
__all__ = [
    "ConversationListView",
    "ConversationDetailView",
    "StartConversationView",
    "SendMessageView",
    "NotificationListView",
    "MarkNotificationReadView",
    "MarkAllNotificationsReadView",
]
