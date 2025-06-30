"""
Notification-related views for the messaging app.

This module contains views for managing notifications, including listing notifications,
marking individual notifications as read, and marking all notifications as read.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.query import QuerySet
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, View

from apps.messaging.models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    """
    View for listing all notifications.

    This view displays all notifications for the current user, ordered by
    creation date (newest first).

    Attributes:
        template_name: The template to render for notification listing.
        context_object_name: The name of the context variable for the notifications.
    """

    template_name = "messaging/notification_list.html"
    context_object_name = "notifications"

    def get_queryset(self) -> QuerySet[Notification]:
        """
        Return only *unread* notifications for the current user so that the
        list view stays consistent with the bell-dropdown, which surfaces just
        the actionable items.
        """
        return Notification.objects.filter(
            user=self.request.user, is_read=False
        ).order_by("-created_at")


class MarkNotificationReadView(LoginRequiredMixin, View):
    """
    View for marking a notification as read.

    This view handles marking a specific notification as read.
    """

    def post(self, request: HttpRequest, pk: int) -> JsonResponse:
        """
        Process a request to mark a notification as read.

        Args:
            request: The HTTP request.
            pk: The ID of the notification to mark as read.

        Returns:
            JsonResponse: JSON response with success status or error message.
        """
        try:
            # Get the notification
            notification = get_object_or_404(Notification, pk=pk, user=request.user)

            # Instead of retaining a read flag we now delete the record to keep
            # the notifications table lean and guarantee bell-menu freshness.
            notification.delete()

            return JsonResponse({"success": True})

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)


class MarkAllNotificationsReadView(LoginRequiredMixin, View):
    """
    View for marking all notifications as read.

    This view handles marking all unread notifications for the current user as read.
    """

    def post(self, request: HttpRequest) -> JsonResponse:
        """
        Process a request to mark all notifications as read.

        Args:
            request: The HTTP request.

        Returns:
            JsonResponse: JSON response with success status, notification count, or error message.
        """
        try:
            # Get all unread notifications
            unread_notifications = Notification.objects.filter(
                user=request.user, is_read=False
            )

            deleted_count = unread_notifications.count()
            unread_notifications.delete()

            return JsonResponse({"success": True, "count": deleted_count})

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
