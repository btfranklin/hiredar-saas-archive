"""
Dashboard and settings views for the recruiters app.

This module contains views for the recruiter dashboard and settings.
"""

from typing import Any, cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import redirect
from django.views.generic import TemplateView

from apps.authentication.types import AuthenticatedUser
from apps.matching.models import CandidateMatch
from apps.messaging.models import Notification
from apps.recruiters.models import JobOpening


class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard view for recruiters."""

    template_name = "recruiters/dashboard.html"

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """Ensure only recruiters can access this view."""
        user = cast(AuthenticatedUser, request.user)
        if user.user_type != "recruiter":
            return redirect("core:home")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Get context data for the dashboard."""
        context = super().get_context_data(**kwargs)
        user = cast(AuthenticatedUser, self.request.user)

        # Get recent job openings
        context["recent_jobs"] = JobOpening.objects.filter(
            recruiter=user.recruiter_profile,
        ).order_by("-created_at")[:5]

        # Get recent candidate matches
        context["recent_matches"] = CandidateMatch.objects.filter(
            job_opening__recruiter=user.recruiter_profile,
            status="pending",
        ).order_by("-match_score")[:5]

        # Get unread notifications
        context["notifications"] = Notification.objects.filter(
            user=cast(Any, user),
            is_read=False,
        ).order_by("-created_at")[:5]

        return context


class SettingsView(LoginRequiredMixin, TemplateView):
    """Settings view for recruiters."""

    template_name = "recruiters/settings.html"

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """Ensure only recruiters can access this view."""
        user = cast(AuthenticatedUser, request.user)
        if user.user_type != "recruiter":
            return redirect("core:home")
        return super().dispatch(request, *args, **kwargs)
