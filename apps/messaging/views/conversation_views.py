"""
Views for handling conversations between users.

This module contains views for listing, viewing, and managing conversations,
including sending messages and handling notifications.
"""

from typing import Any, cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseBase, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.generic import DetailView, ListView, View

from apps.authentication.models import User
from apps.messaging.models import Conversation, Message, Notification


class ConversationListView(LoginRequiredMixin, ListView):
    """
    View for listing user's conversations.

    This view displays all conversations the user is part of, along with
    unread message counts and recent notifications.
    """

    template_name = "messaging/conversation_list.html"
    context_object_name = "conversations"

    def get_queryset(self) -> QuerySet[Conversation]:
        """Get conversations for the current user."""
        return (
            Conversation.objects.filter(participants=self.request.user)
            .order_by("-updated_at")
            .distinct()
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Get context data for rendering the template.

        Adds unread notifications to the context.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            dict: The context data for the template.
        """
        context = super().get_context_data(**kwargs)

        # Get unread notifications
        context["notifications"] = (
            Notification.objects.filter(user=self.request.user, is_read=False)
            .order_by("-created_at")
            .distinct()
        )

        # Get unread message counts for each conversation
        for conversation in context["conversations"]:
            conversation.unread_count = (
                Message.objects.filter(
                    conversation=conversation,
                    is_read=False,
                )
                .exclude(sender=self.request.user)
                .count()
            )

        return context


class ConversationDetailView(LoginRequiredMixin, DetailView):
    """
    View for displaying a conversation.

    This view shows the conversation history and allows sending new messages.
    It also handles marking messages as read.
    """

    template_name = "messaging/conversation_detail.html"
    model = Conversation

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """
        Check if the user is a participant before processing the request.

        Args:
            request: The HTTP request.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: The response to the request.
        """
        conversation: Conversation = self.get_object()
        # Cast request.user to type Any to bypass type checking for Django's dynamic behavior
        user = cast(Any, request.user)
        if user not in conversation.participants.all():
            return redirect("messaging:conversation_list")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Get context data for rendering the template.

        Adds messages and other participant to the context.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            dict: The context data for the template.
        """
        context = super().get_context_data(**kwargs)
        conversation: Conversation = self.get_object()

        # Get messages and mark them as read
        # Since the type checker can't infer the related_name, we need to use getattr
        message_queryset = getattr(conversation, "messages").order_by("-created_at")
        message_queryset.filter(is_read=False).exclude(sender=self.request.user).update(
            is_read=True
        )

        context["messages"] = message_queryset
        # Cast request.user to Any to bypass strict type checking with Django's ORM
        user = cast(Any, self.request.user)
        context["other_participant"] = conversation.get_other_participant(
            user
        )

        return context


class StartConversationView(LoginRequiredMixin, View):
    """
    View for starting a new conversation.

    This view handles creating a new conversation between users,
    optionally linking it to a job opening.
    """

    def post(
        self, request: HttpRequest, user_id: int, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        """
        Handle POST request to start a new conversation.

        Args:
            request: The HTTP request.
            user_id: The ID of the user to start a conversation with.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            JsonResponse: Response indicating success or failure.
        """
        try:
            recipient = get_object_or_404(User, id=user_id)

            # Check if conversation already exists
            existing_conversation = (
                Conversation.objects.filter(participants=request.user)
                .filter(participants=recipient)
                .first()
            )

            if existing_conversation:
                return JsonResponse(
                    {
                        "status": "success",
                        "redirect_url": reverse(
                            "messaging:conversation_detail",
                            kwargs={"pk": existing_conversation.pk},
                        ),
                    }
                )

            # Create new conversation
            conversation = Conversation.objects.create()
            # Cast user objects to Any to satisfy type checker with Django's ORM
            conversation.participants.add(cast(Any, request.user), cast(Any, recipient))

            # Create initial message if provided
            message_content = request.POST.get("message", "")
            if message_content:
                Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    content=message_content,
                )

            # Create notification for recipient
            Notification.objects.create(
                user=recipient,
                notification_type="message",
                content=f"New message from {cast(Any, request.user).get_full_name()}",
                link=reverse(
                    "messaging:conversation_detail", kwargs={"pk": conversation.pk}
                ),
            )

            return JsonResponse(
                {
                    "status": "success",
                    "redirect_url": reverse(
                        "messaging:conversation_detail",
                        kwargs={"pk": conversation.pk},
                    ),
                }
            )

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})


class SendMessageView(LoginRequiredMixin, View):
    """
    View for sending a message in a conversation.

    This view handles creating new messages and notifications.
    """

    def post(
        self, request: HttpRequest, pk: int, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        """
        Handle POST request to send a message.

        Args:
            request: The HTTP request.
            pk: The ID of the conversation.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            JsonResponse: Response with the rendered message HTML.
        """
        try:
            conversation = get_object_or_404(Conversation, pk=pk)

            # Check if user is participant
            # Cast to Any to bypass type checking
            if cast(Any, request.user) not in conversation.participants.all():
                return JsonResponse(
                    {"status": "error", "message": "Not authorized"}, status=403
                )

            # Create message
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=request.POST.get("message", ""),
            )

            # Create notification for recipient
            recipient = conversation.get_other_participant(cast(Any, request.user))
            if recipient:
                Notification.objects.create(
                    user=recipient,
                    notification_type="message",
                    content=f"New message from {cast(Any, request.user).get_full_name()}",
                    link=reverse(
                        "messaging:conversation_detail", kwargs={"pk": conversation.pk}
                    ),
                )

            # Render message HTML
            message_html = render_to_string(
                "messaging/components/message.html",
                {"message": message},
                request=request,
            )

            return JsonResponse({"status": "success", "message_html": message_html})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
