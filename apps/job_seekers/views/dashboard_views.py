"""Dashboard views for job seekers."""

from typing import Any, cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import redirect
from django.views.generic import TemplateView

from apps.authentication.types import AuthenticatedUser
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

        # Get job matches
        context["job_matches"] = CandidateMatch.objects.filter(
            job_seeker=user.job_seeker_profile,
            status="pending",
        ).order_by("-match_score")[:5]

        # Get unread notifications
        context["notifications"] = Notification.objects.filter(
            user=cast(
                Any, user
            ),  # Cast to Any to avoid type incompatibility with the model field
            is_read=False,
        ).order_by("-created_at")[:5]

        return context
