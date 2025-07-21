"""Views for the Job Seeker Workshop feature."""

from __future__ import annotations

from typing import Any, cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, HttpResponseBase, JsonResponse
from django.shortcuts import redirect, render
from django.views import View

from apps.authentication.types import AuthenticatedUser
from apps.job_seekers.services import ProfileManager
from apps.job_seekers.services.workshop_service import (
    generate_targeted_documents,
    upgrade_resume_content,
)


class WorkshopLandingView(LoginRequiredMixin, View):
    """Landing page that lists available workshop tools."""

    template_name = "job_seekers/workshop_landing.html"

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:  # type: ignore[override]
        """Ensure only job seeker users can access this view."""
        user = cast(AuthenticatedUser, request.user)
        if not user.is_authenticated or user.user_type != "job_seeker":
            return redirect("core:home")

        # Ensure profile exists
        if not ProfileManager.get_profile_for_user(user):
            return redirect("job_seekers:profile_create")

        return super().dispatch(request, *args, **kwargs)

    def get(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponse:  # noqa: D401
        """Render the workshop page."""
        user = cast(AuthenticatedUser, request.user)
        profile = ProfileManager.get_profile_for_user(user)
        personal_tagline = getattr(profile, "personal_tagline", None) or "Job Seeker"
        context: dict[str, Any] = {
            "active_page": "workshop",
            "personal_tagline": personal_tagline,
        }
        return render(request, self.template_name, context)


# ---------------------------------------------------------------------------
# Tool Views
# ---------------------------------------------------------------------------


class UpgradeResumeView(LoginRequiredMixin, View):
    """View for upgrading resume."""

    template_name = "job_seekers/workshop_upgrade_resume.html"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        user = cast(AuthenticatedUser, request.user)
        profile = ProfileManager.get_profile_for_user(user)
        personal_tagline = getattr(profile, "personal_tagline", None) or "Job Seeker"
        context = {
            "active_page": "workshop",
            "personal_tagline": personal_tagline,
        }
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        user = cast(AuthenticatedUser, request.user)
        profile = ProfileManager.get_profile_for_user(user)
        if profile is None:
            return JsonResponse(
                {"status": "error", "message": "Profile not found."}, status=400
            )
        from apps.job_seekers.models.profile import JobSeekerProfile

        content = upgrade_resume_content(cast(JobSeekerProfile, profile))
        return JsonResponse({"status": "success", "resume": content})


class TargetedDocsView(LoginRequiredMixin, View):
    """View for generating targeted resume and cover letter."""

    template_name = "job_seekers/workshop_targeted_docs.html"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        user = cast(AuthenticatedUser, request.user)
        profile = ProfileManager.get_profile_for_user(user)
        personal_tagline = getattr(profile, "personal_tagline", None) or "Job Seeker"
        context = {
            "active_page": "workshop",
            "personal_tagline": personal_tagline,
        }
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        job_description = request.POST.get("job_description", "")
        if not job_description:
            return JsonResponse(
                {"status": "error", "message": "Job description required."}, status=400
            )

        user = cast(AuthenticatedUser, request.user)
        profile = ProfileManager.get_profile_for_user(user)
        if profile is None:
            return JsonResponse(
                {"status": "error", "message": "Profile not found."}, status=400
            )

        from apps.job_seekers.models.profile import JobSeekerProfile

        docs = generate_targeted_documents(
            cast(JobSeekerProfile, profile), job_description
        )
        return JsonResponse({"status": "success", **docs})
