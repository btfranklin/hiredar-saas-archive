"""
Recruiter-facing views for candidate profiles.
"""

from __future__ import annotations

from typing import Any, cast

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import redirect
from django.views.generic import DetailView

from apps.authentication.types import AuthenticatedUser
from apps.candidates.models import CandidateProfile


class ResumeView(LoginRequiredMixin, DetailView):
    """Allow recruiters to view the parsed résumé for a candidate profile."""

    model = CandidateProfile
    template_name = "candidates/resume_view.html"
    context_object_name = "profile"

    def dispatch(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponseBase:
        """Ensure the authenticated recruiter owns the candidate pool."""
        user = cast(AuthenticatedUser, request.user)

        if user.user_type != "recruiter":
            messages.error(request, "Only recruiters can view candidate résumés.")
            return redirect("core:home")

        profile = self.get_object()
        if profile.pool and profile.pool.recruiter == user:
            return super().dispatch(request, *args, **kwargs)

        messages.error(
            request,
            "This résumé is not available outside of your candidate pools.",
        )
        return redirect("recruiters:dashboard")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Provide additional context required by the template."""
        context = super().get_context_data(**kwargs)
        context["conversation"] = None
        context["job_opening"] = None
        return context
