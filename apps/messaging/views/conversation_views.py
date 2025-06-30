"""
Views for handling conversations between users.

This module contains views for listing, viewing, and managing conversations,
including sending messages and handling notifications.
"""

from typing import Any, cast

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseBase, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.generic import DetailView, ListView, View

from apps.authentication.models import User
from apps.job_seekers.services import ProfileManager
from apps.matching.models import CandidateMatch
from apps.messaging.models import Conversation, Message, Notification
from apps.recruiters.models import JobOpening


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
        qs = Conversation.objects.filter(participants=self.request.user)

        # Hide pre-interest conversations for recruiters
        if getattr(self.request.user, "user_type", "") == "recruiter":
            qs = qs.exclude(status="interest_requested")

        return qs.order_by("-updated_at").distinct()

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
            # Determine other participant relative to current user for accurate display
            # (Cannot assign to the property 'other_participant', so store under a
            # different attribute that the template can use.)
            conversation.display_other_participant = conversation.get_other_participant(
                cast(Any, self.request.user)
            )

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

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
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

        # Clear any Django messages to prevent toast pop-ups in this view
        list(messages.get_messages(request))
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
        # Display messages in chronological order (oldest first) so that the
        # newest messages appear at the bottom, which matches typical chat UX.
        message_queryset = getattr(conversation, "messages").order_by("created_at")
        message_queryset.filter(is_read=False).exclude(sender=self.request.user).update(
            is_read=True
        )

        # Remove any matching unread notifications entirely so they disappear from
        # the bell dropdown once the candidate opens the conversation detail.
        conv_url = reverse(
            "messaging:conversation_detail", kwargs={"pk": conversation.pk}
        )
        Notification.objects.filter(
            user=self.request.user, link=conv_url, is_read=False
        ).delete()

        # Use a non-conflicting key name so it does not shadow Django's built-in
        # `messages` context processor (which powers flash/alert messages in
        # the base template). Shadowing it caused every `Message` instance to
        # be rendered as a toast in the UI because the base template loops over
        # a variable called `messages`.  By renaming the key we eliminate the
        # accidental collision and the unwanted pop-ups.
        context["conversation_messages"] = message_queryset
        # Cast request.user to Any to bypass strict type checking with Django's ORM
        user = cast(Any, self.request.user)
        context["other_participant"] = conversation.get_other_participant(user)

        # Add job opening to context if it exists
        if conversation.job_opening:
            context["job_opening"] = conversation.job_opening

        # For recruiters, supply the candidate's JobSeekerProfile primary key for resume links
        if (
            getattr(self.request.user, "user_type", "") == "recruiter"
            and context["other_participant"] is not None
            and getattr(context["other_participant"], "user_type", "") == "job_seeker"
        ):
            try:
                from apps.job_seekers.models import JobSeekerProfile  # local import

                profile = JobSeekerProfile.objects.get(
                    user_owner=context["other_participant"]
                )
                context["job_seeker_profile_id"] = profile.pk
            except Exception:
                context["job_seeker_profile_id"] = None

        # Provide match object for candidate system card
        if (
            conversation.status == "interest_requested"
            and getattr(self.request.user, "user_type", "") == "job_seeker"
            and conversation.job_opening
        ):
            try:
                profile = ProfileManager.get_profile_for_user(self.request.user)
                match_obj = CandidateMatch.objects.get(
                    job_opening=conversation.job_opening,
                    talent_sheet__job_seeker=profile,
                )
                context["candidate_match"] = match_obj
            except Exception:
                context["candidate_match"] = None

        return context


class StartConversationView(LoginRequiredMixin, View):
    """
    View for starting a new conversation.

    This view handles creating a new conversation between users,
    optionally linking it to a job opening.
    """

    def post(
        self,
        request: HttpRequest,
        job_id: int,
        recipient_id: int,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """
        Handle POST request to start a new conversation.

        Args:
            request: The HTTP request.
            job_id: The ID of the job opening this conversation is about.
            recipient_id: The ID of the user to start a conversation with.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: Appropriate response based on request type (HTMX or regular).
        """
        try:
            # Verify the current user is a recruiter
            if cast(Any, request.user).user_type != "recruiter":
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Only recruiters can initiate conversations",
                    },
                    status=403,
                )

            # Allow recipient_id to be either a User ID or a JobSeekerProfile ID
            try:
                recipient = User.objects.get(id=recipient_id)
            except User.DoesNotExist:
                try:
                    from apps.job_seekers.models import (
                        JobSeekerProfile,  # local import to avoid circular
                    )

                    profile = JobSeekerProfile.objects.get(id=recipient_id)
                    recipient = profile.user_owner
                except JobSeekerProfile.DoesNotExist:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "Recipient not found",
                        },
                        status=404,
                    )

            job_opening = get_object_or_404(JobOpening, id=job_id)

            # Verify the job belongs to the recruiter
            if job_opening.recruiter.user != request.user:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "You can only create conversations for your own job openings",
                    },
                    status=403,
                )

            # Check if conversation already exists for this job and recipient
            existing_conversation = (
                Conversation.objects.filter(participants=request.user)
                .filter(participants=recipient)
                .filter(job_opening=job_opening)
                .first()
            )

            redirect_url = ""
            if existing_conversation:
                redirect_url = reverse(
                    "messaging:conversation_detail",
                    kwargs={"pk": existing_conversation.pk},
                )
            else:
                # Create new conversation
                conversation = Conversation.objects.create(
                    job_opening=job_opening, status="interest_requested"
                )
                # Cast user objects to Any to satisfy type checker with Django's ORM
                conversation.participants.add(
                    cast(Any, request.user), cast(Any, recipient)
                )

                # Create notification for recipient
                Notification.objects.create(
                    user=recipient,
                    notification_type="match",  # Use match instead of message to indicate interest check
                    content=f"New job opportunity from {cast(Any, request.user).get_full_name()}",
                    link=reverse(
                        "messaging:conversation_detail", kwargs={"pk": conversation.pk}
                    ),
                )

                redirect_url = reverse(
                    "messaging:conversation_detail",
                    kwargs={"pk": conversation.pk},
                )

            # If HTMX request, return updated contact-controls HTML instead of redirect
            if "HX-Request" in request.headers:
                from django.template.loader import render_to_string

                # Always allow contact here because this endpoint is only
                # reached for public-pool candidates who have a `user_owner`.
                html = render_to_string(
                    "matching/partials/contact_controls.html",
                    {
                        "candidate_conversation": (
                            conversation
                            if not existing_conversation
                            else existing_conversation
                        ),
                        "is_shortlisted": False,
                        "job_opening": job_opening,
                        "job_seeker_id": recipient.pk,
                        "show_contact": True,
                        "show_shortlist": True,
                    },
                    request=request,
                )

                response = HttpResponse(html, headers={"HX-Reswap": "outerHTML"})
                response["HX-Trigger"] = (
                    '{"closeModal": {"id": "confirm-interest-modal"}}'
                )
                return response
            else:
                # For non-HTMX requests (API), return JSON response with redirect URL
                return JsonResponse(
                    {
                        "status": "success",
                        "redirect_url": redirect_url,
                    }
                )

        except Exception as e:
            if "HX-Request" in request.headers:
                # For HTMX requests, return error message as HTML
                return HttpResponse(
                    f"<div class='alert alert-error'>Error: {str(e)}</div>", status=500
                )
            else:
                # For non-HTMX requests, return JSON error
                return JsonResponse({"status": "error", "message": str(e)}, status=500)


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

            # Determine allowed conversation states
            ALLOWED_STATUSES = ["active", "candidate_interested"]

            if conversation.status not in ALLOWED_STATUSES:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Cannot send messages in the current conversation state",
                    },
                    status=400,
                )

            # If candidate already said yes but conversation not promoted to active yet
            if conversation.status == "candidate_interested":
                conversation.status = "active"
                conversation.save(update_fields=["status"])

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
            if "HX-Request" in request.headers:
                html = render_to_string(
                    "messaging/components/message.html",
                    {"message": message},
                    request=request,
                )
                return HttpResponse(html, headers={"HX-Reswap": "beforeend"})

            # Non-HTMX fallback
            message_html = render_to_string(
                "messaging/components/message.html",
                {"message": message},
                request=request,
            )

            return JsonResponse({"status": "success", "message_html": message_html})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})


class RespondToInterestView(LoginRequiredMixin, View):
    """
    View for job seekers to respond to interest checks.

    This view handles updating conversation status based on the job seeker's response.
    """

    def post(
        self, request: HttpRequest, pk: int, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        """
        Handle POST request to respond to an interest check.

        Args:
            request: The HTTP request.
            pk: The ID of the conversation.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            JsonResponse: Response indicating success or failure.
        """
        try:
            conversation = get_object_or_404(Conversation, pk=pk)

            # Verify the current user is a participant and a job seeker
            if (
                cast(Any, request.user) not in conversation.participants.all()
                or cast(Any, request.user).user_type != "job_seeker"
            ):
                return JsonResponse(
                    {"status": "error", "message": "Not authorized"}, status=403
                )

            # Verify the conversation is in interest_requested status
            if conversation.status != "interest_requested":
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "This conversation has already been responded to",
                    },
                    status=400,
                )

            # Get response (interested or not interested)
            is_interested = request.POST.get("is_interested") == "true"
            new_status = (
                "candidate_interested" if is_interested else "candidate_not_interested"
            )

            # Update conversation status
            conversation.status = new_status
            conversation.save()

            # If Interested, notify recruiter. We no longer create a textual
            # message for either response – the UI now reflects the status via
            # banners/badges only.
            if is_interested:
                recruiter = conversation.get_other_participant(cast(Any, request.user))

                Notification.objects.create(
                    user=recruiter,
                    notification_type="match",
                    content=f"{cast(Any, request.user).get_full_name()} is interested in your job opening!",
                    link=reverse(
                        "messaging:conversation_detail", kwargs={"pk": conversation.pk}
                    ),
                )

            # If HTMX request, return updated interest card HTML so client can
            # swap it without a full page reload.
            if "HX-Request" in request.headers:
                html = render_to_string(
                    "messaging/partials/interest_card.html",
                    {
                        "conversation": conversation,
                        "job_opening": conversation.job_opening,
                        # candidate_match may or may not exist – reuse earlier logic
                        "candidate_match": None,
                    },
                    request=request,
                )

                resp = HttpResponse(html, headers={"HX-Reswap": "outerHTML"})

                modal_id = (
                    "confirm-not-interested-modal"
                    if not is_interested
                    else "confirm-interested-modal"
                )
                resp["HX-Trigger"] = '{"closeModal": {"id": "' + modal_id + '"}}'

                return resp

            # Non-HTMX fallback
            return JsonResponse({"status": "success"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
