"""Dashboard views for job seekers."""

from typing import Any, cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models  # <- add this along existing imports
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import redirect
from django.views.generic import ListView, TemplateView

from apps.authentication.types import AuthenticatedUser
from apps.job_seekers.models import RoleRecommendation, TalentSheet
from apps.job_seekers.services import ProfileManager
from apps.matching.models import CandidateMatch
from apps.messaging.models import Message, Notification


class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard view for job seekers."""

    template_name = "job_seekers/dashboard.html"

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """Ensure only job seekers can access this view."""
        user = cast(AuthenticatedUser, request.user)
        if user.user_type != "job_seeker":
            return redirect("core:home")

        # Check if job seeker profile exists, if not redirect to profile creation
        try:
            # This will raise RelatedObjectDoesNotExist if profile doesn't exist
            ProfileManager.get_profile_for_user(user)
        except Exception:
            # Redirect to profile creation page
            return redirect("job_seekers:profile_create")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Get context data for the dashboard."""
        context = super().get_context_data(**kwargs)
        user = cast(AuthenticatedUser, self.request.user)
        profile = ProfileManager.get_profile_for_user(user)

        # Get job matches
        context["job_matches"] = CandidateMatch.objects.filter(
            talent_sheet__job_seeker=profile,
            status="pending",
        ).order_by("-created_at")[:5]

        # Get unread notifications
        context["notifications"] = Notification.objects.filter(
            user=cast(
                Any, user
            ),  # Cast to Any to avoid type incompatibility with the model field
            is_read=False,
        ).order_by("-created_at")[:5]

        # Get role recommendations
        # First, get roles the user is interested in
        context["interested_roles"] = RoleRecommendation.objects.filter(
            job_seeker=profile,
            is_candidate_interested=True,
        ).order_by("role_title")[:5]

        # Then, get other role recommendations
        context["other_roles"] = RoleRecommendation.objects.filter(
            job_seeker=profile,
            is_candidate_interested=False,
        ).order_by("role_title")[:5]

        # Get total count for the stats card
        context["recommended_roles_count"] = RoleRecommendation.objects.filter(
            job_seeker=profile
        ).count()

        # Include the talent pool status based on talent sheet publication
        context["in_talent_pool"] = (
            profile.in_talent_pool if profile is not None else False
        )

        # Include the personal tagline directly in the context for sidebar rendering
        context["personal_tagline"] = (
            getattr(profile, "personal_tagline", None) or "Job Seeker"
        )

        # ---------------------------------------------------
        # Recent Messages & Interest Requests Panel
        # ---------------------------------------------------

        # 1. Actual message objects
        message_records = list(
            Message.objects.filter(conversation__participants=user)
            .order_by("-created_at")
            .select_related("sender")[:20]  # grab a few extra for later slicing
        )

        # 2. Conversations where a recruiter has sent an interest request but no messages yet

        from apps.messaging.models import Conversation  # local import to avoid circular

        interest_conversations = (
            Conversation.objects.filter(participants=user, status="interest_requested")
            .annotate(message_count=models.Count("messages"))
            .filter(message_count=0)
            .order_by("-created_at")[:20]
        )

        # Build a unified list-like structure
        recent_messages: list[dict[str, Any]] = []

        # Add actual messages
        for msg in message_records:
            recent_messages.append(
                {
                    "sender": msg.sender,
                    "text": msg.content,
                    "created_at": msg.created_at,
                    "is_unread": (not msg.is_read and msg.sender != user),
                    "conversation_id": msg.conversation.pk,
                }
            )

        # Add interest requests (pseudo-messages)
        for conv in interest_conversations:
            recruiter = conv.get_other_participant(cast(Any, user))
            if recruiter is None:
                continue
            job_title = getattr(conv.job_opening, "title", "a new opportunity")
            recent_messages.append(
                {
                    "sender": recruiter,
                    "text": f"Recruiter is interested in discussing {job_title}",
                    "created_at": conv.created_at,
                    "is_unread": True,
                    "conversation_id": conv.id,
                }
            )

        # Sort by newest and take top 5
        recent_messages.sort(key=lambda item: item["created_at"], reverse=True)
        context["recent_messages"] = recent_messages[:5]

        return context


class RoleRecommendationsView(LoginRequiredMixin, ListView):
    """
    View for listing role recommendations for a job seeker.

    This view displays role recommendations for job seekers based on their
    skills and experience. Only accessible to job seekers.

    Attributes:
        template_name: The template to render for role recommendations.
        context_object_name: The name of the context variable for the recommendations.
    """

    template_name = "job_seekers/role_recommendations.html"
    context_object_name = "role_recommendations"

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """
        Check if the user is a job seeker before processing the request.

        Args:
            request: The HTTP request.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponseBase: The response to the request.
        """
        user = cast(AuthenticatedUser, request.user)
        if not user.is_authenticated or user.user_type != "job_seeker":
            return redirect("core:home")

        if not ProfileManager.get_profile_for_user(user):
            return redirect("job_seekers:profile_create")

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[RoleRecommendation]:
        """
        Get the role recommendations to display for the job seeker.

        Returns:
            QuerySet[RoleRecommendation]: A queryset of role recommendations for the job seeker.
        """
        user = cast(AuthenticatedUser, self.request.user)
        return RoleRecommendation.objects.filter(
            job_seeker=ProfileManager.get_profile_for_user(user)
        ).order_by("role_title")


class TalentSheetDetailsView(LoginRequiredMixin, TemplateView):
    """
    View for displaying talent sheet details.

    This view renders a partial template with the talent sheet information
    for the job seeker. It is designed to be loaded via HTMX when the
    talent sheet collapse is expanded.
    """

    template_name = "job_seekers/components/talent_sheet_details.html"

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """
        Check if the user is a job seeker before processing the request.

        Args:
            request: The HTTP request.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponseBase: The response to the request.
        """
        user = cast(AuthenticatedUser, request.user)
        if not user.is_authenticated or user.user_type != "job_seeker":
            return redirect("core:home")

        if not ProfileManager.get_profile_for_user(user):
            return redirect("job_seekers:profile_create")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Get the talent sheet details for the job seeker.

        Returns:
            dict[str, Any]: Context data including the talent sheet information.
        """
        context = super().get_context_data(**kwargs)
        user = cast(AuthenticatedUser, self.request.user)

        try:
            # Get the job seeker and talent sheet
            job_seeker = ProfileManager.get_profile_for_user(user)
            talent_sheet = TalentSheet.objects.get(job_seeker=job_seeker)
            context["talent_sheet"] = talent_sheet
            context["has_talent_sheet"] = True
        except TalentSheet.DoesNotExist:
            context["has_talent_sheet"] = False

        return context
