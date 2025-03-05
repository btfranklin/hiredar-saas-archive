"""
Views for the messaging app.

This module imports and exposes all views from the messaging app's view modules,
making them available for import directly from apps.messaging.views.
"""

from apps.messaging.views.conversation_views import (ConversationDetailView,
                                                     ConversationListView,
                                                     SendMessageView,
                                                     StartConversationView)
from apps.messaging.views.notification_views import (
    MarkAllNotificationsReadView, MarkNotificationReadView,
    NotificationListView)

# For backwards compatibility, expose all views at the module level
__all__ = [
    "ConversationListView",
    "ConversationDetailView",
    "StartConversationView",
    "SendMessageView",
    "NotificationListView",
    "MarkNotificationReadView",
    "MarkAllNotificationsReadView",
]
