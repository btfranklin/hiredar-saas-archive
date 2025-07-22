"""Views for the Job Seeker Workshop feature."""

from __future__ import annotations

from typing import Any, cast

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseBase,
    JsonResponse,
)
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import smart_str
from django.views import View

from apps.authentication.types import AuthenticatedUser
from apps.job_seekers.models.profile import JobSeekerProfile
from apps.job_seekers.services import ProfileManager
from apps.job_seekers.services.workshop_service import (
    generate_targeted_documents,
    parse_resume_markdown,
    upgrade_resume_content,
)

# ---------------------------------------------------------------------------
# Rate-limit configuration
# ---------------------------------------------------------------------------

DAILY_LIMIT = getattr(settings, "JOBSEEKERS_WORKSHOP_DAILY_LIMIT", 10)
TTL_SECONDS = 24 * 60 * 60  # 24 hours


def _get_cache_key(user_id: int) -> str:
    return f"resume_upgrade:{user_id}"


def _increment_usage(user_id: int) -> int:
    """Atomically increment and return today's usage counter for the user."""

    key = _get_cache_key(user_id)
    try:
        return cache.incr(key)
    except ValueError:
        # Key doesn't exist yet → create with TTL
        cache.add(key, 1, TTL_SECONDS)
        return 1


def _current_usage(user_id: int) -> int:
    return cache.get(_get_cache_key(user_id), 0)


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
        user_id: int = getattr(user, "id", 0)  # type: ignore[attr-defined]
        usage = _current_usage(user_id)
        remaining = max(DAILY_LIMIT - usage, 0)
        context = {
            "active_page": "workshop",
            "personal_tagline": personal_tagline,
            "remaining_upgrades": remaining,
        }
        return render(request, self.template_name, context)

    def post(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:  # noqa: C901 – complexity fine for view
        """Handle HTMX POST requests that trigger the upgrade flow.

        Returns an HTML fragment that replaces the ``#upgrade-output`` element
        on the page. The fragment shows the upgraded resume using the existing
        resume detail component **plus** controls for downloading / applying
        the result.
        """

        # Rate-limit: ensure the user hasn't exceeded the daily quota *before*
        # we hit the LLM.
        user = cast(AuthenticatedUser, request.user)
        user_id: int = getattr(user, "id", 0)  # type: ignore[attr-defined]
        usage_before = _current_usage(user_id)
        if usage_before >= DAILY_LIMIT:
            # Return partial with ghost button – no further processing
            return render(
                request,
                "job_seekers/partials/limit_reached.html",
                {"remaining_upgrades": 0},
                status=429,
            )

        # Record this attempt (atomically)
        current_usage = _increment_usage(user_id)

        if current_usage > DAILY_LIMIT:
            # Edge-case: another request raced ahead and used the last slot
            return render(
                request,
                "job_seekers/partials/limit_reached.html",
                {"remaining_upgrades": 0},
                status=429,
            )

        # Ensure we are dealing with a job-seeker profile
        user = cast(AuthenticatedUser, request.user)
        profile = ProfileManager.get_profile_for_user(user)
        if profile is None:
            return HttpResponseBadRequest("Profile not found.")

        # Call service layer (OpenAI etc.)
        upgraded_markdown: str = upgrade_resume_content(cast(JobSeekerProfile, profile))

        # Keep a copy in the session for later download / application actions
        request.session["upgraded_resume_markdown"] = upgraded_markdown

        # Parse the markdown into a very small stand-in so the existing
        # component can render it nicely.
        parsed_profile = parse_resume_markdown(upgraded_markdown)

        # Render partial and return to HTMX caller
        return render(
            request,
            "job_seekers/partials/upgraded_resume.html",
            {
                "profile": parsed_profile,
                "resume_text": upgraded_markdown,
                "remaining_upgrades": max(DAILY_LIMIT - current_usage, 0),
            },
        )


# ---------------------------------------------------------------------------
# Follow-up actions for the upgraded resume
# ---------------------------------------------------------------------------


class DownloadUpgradedResumeView(LoginRequiredMixin, View):
    """Serve the upgraded resume as a downloadable file (PDF fallback to TXT)."""

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        resume_md: str | None = request.session.get("upgraded_resume_markdown")
        if not resume_md:
            return HttpResponseBadRequest(
                "No upgraded resume available – please run the upgrade first."
            )

        # For now we provide the Markdown as a `.txt` file. Converting to PDF
        # or DOCX can be added later.
        filename = "upgraded_resume.txt"
        response = HttpResponse(resume_md, content_type="text/plain")
        response["Content-Disposition"] = f"attachment; filename={smart_str(filename)}"
        return response


class ApplyUpgradedResumeView(LoginRequiredMixin, View):
    """Treat the upgraded resume *as if* the user had uploaded it."""

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        resume_md: str | None = request.session.get("upgraded_resume_markdown")
        if not resume_md:
            return HttpResponseBadRequest("No upgraded resume data found in session.")

        user = cast(AuthenticatedUser, request.user)
        profile = ProfileManager.get_profile_for_user(user)
        if profile is None:
            return HttpResponseBadRequest("Profile not found.")

        # ------------------------------------------------------------------
        # VERY lightweight: we simply parse the markdown and persist the main
        # sections directly onto the user's profile. This mimics the intent of
        # the regular upload pipeline without the heavy async processing.
        # ------------------------------------------------------------------

        parsed_profile = parse_resume_markdown(resume_md)

        # Copy recognised attributes over to the real profile
        for attr in (
            "professional_summary",
            "experience",
            "education",
            "certifications",
            "skills",
        ):
            if hasattr(parsed_profile, attr):
                setattr(profile, attr, getattr(parsed_profile, attr))

        profile.save()

        # Redirect the client to the regular profile page (HTMX redirect).
        response = HttpResponse()
        response["HX-Redirect"] = reverse("job_seekers:profile")
        return response


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

        docs = generate_targeted_documents(
            cast(JobSeekerProfile, profile), job_description
        )
        return JsonResponse({"status": "success", **docs})
