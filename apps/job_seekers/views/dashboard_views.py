"""Dashboard views for job seekers."""

from typing import Any, cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import redirect
from django.views.generic import ListView, TemplateView

from apps.authentication.types import AuthenticatedUser
from apps.job_seekers.models import RoleRecommendation
from apps.jobs.models import CandidateMatch
from apps.messaging.models import Notification


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
            user.job_seeker_profile
        except Exception:
            # Redirect to profile creation page
            return redirect("job_seekers:profile_create")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Get context data for the dashboard."""
        context = super().get_context_data(**kwargs)
        user = cast(AuthenticatedUser, self.request.user)
        profile = user.job_seeker_profile

        # Get job matches
        context["job_matches"] = CandidateMatch.objects.filter(
            job_seeker=profile,
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

        if not hasattr(user, "job_seeker_profile"):
            return redirect("job_seekers:create_profile")

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[RoleRecommendation]:
        """
        Get the role recommendations to display for the job seeker.

        Returns:
            QuerySet[RoleRecommendation]: A queryset of role recommendations for the job seeker.
        """
        user = cast(AuthenticatedUser, self.request.user)
        return RoleRecommendation.objects.filter(
            job_seeker=user.job_seeker_profile
        ).order_by("role_title")
