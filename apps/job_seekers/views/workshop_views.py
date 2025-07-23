"""Views for the Job Seeker Workshop feature."""

# pylint: disable=not-callable

from __future__ import annotations

import time
from typing import Any, cast
from uuid import uuid4

from celery import chain
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
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

from apps.authentication.models import User
from apps.authentication.types import AuthenticatedUser
from apps.job_seekers.models import TalentSheet
from apps.job_seekers.models.profile import JobSeekerProfile
from apps.job_seekers.services import ProfileManager
from apps.job_seekers.services.talent_pool_manager import TalentPoolManager
from apps.job_seekers.services.workshop_service import (
    optimize_linkedin_content,
    parse_linkedin_markdown,
    parse_resume_markdown,
    upgrade_resume_content,
)
from apps.job_seekers.tasks.post_resume_processing_tasks import (
    resume_processing_completed,
)
from apps.job_seekers.views.mixins import HTMXViewMixin, ProfileAccessMixin
from apps.resume_processing.services.resume_processor import ResumeProcessor
from apps.resume_processing.tasks.resume_processing_tasks import (
    handle_resume_upload_task,
)

# ---------------------------------------------------------------------------
# Rate-limit configuration
# ---------------------------------------------------------------------------

DAILY_LIMIT = getattr(settings, "JOBSEEKERS_WORKSHOP_DAILY_LIMIT", 10)
TTL_SECONDS = 24 * 60 * 60  # 24 hours

# Separate limit for LinkedIn optimization (can map to same env var fallback)
LINKEDIN_DAILY_LIMIT = getattr(
    settings, "JOBSEEKERS_WORKSHOP_LINKEDIN_DAILY_LIMIT", DAILY_LIMIT
)


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


# ---------------------------------------------------------------------------
# LinkedIn tool rate-limit helpers (separate cache key to track independently)
# ---------------------------------------------------------------------------


def _get_cache_key_linkedin(user_id: int) -> str:
    return f"linkedin_optimize:{user_id}"


def _increment_usage_linkedin(user_id: int) -> int:
    key = _get_cache_key_linkedin(user_id)
    try:
        return cache.incr(key)
    except ValueError:
        cache.add(key, 1, TTL_SECONDS)
        return 1


def _current_usage_linkedin(user_id: int) -> int:
    return cache.get(_get_cache_key_linkedin(user_id), 0)


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
# Optimize LinkedIn View
# ---------------------------------------------------------------------------


class OptimizeLinkedInView(LoginRequiredMixin, View):
    """View for creating an optimized LinkedIn headline and About section."""

    template_name = "job_seekers/workshop_optimize_linkedin.html"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        user = cast(AuthenticatedUser, request.user)
        profile = ProfileManager.get_profile_for_user(user)
        personal_tagline = getattr(profile, "personal_tagline", None) or "Job Seeker"
        user_id: int = getattr(user, "id", 0)  # type: ignore[attr-defined]
        remaining = max(LINKEDIN_DAILY_LIMIT - _current_usage_linkedin(user_id), 0)
        context = {
            "active_page": "workshop",
            "personal_tagline": personal_tagline,
            "remaining_generations": remaining,
        }
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """Handle HTMX POST requests that generate the LinkedIn content."""

        user = cast(AuthenticatedUser, request.user)
        user_id: int = getattr(user, "id", 0)  # type: ignore[attr-defined]

        usage_before = _current_usage_linkedin(user_id)
        if usage_before >= LINKEDIN_DAILY_LIMIT:
            return render(
                request,
                "job_seekers/partials/limit_reached.html",
                {"remaining_upgrades": 0},
                status=429,
            )

        current_usage = _increment_usage_linkedin(user_id)
        if current_usage > LINKEDIN_DAILY_LIMIT:
            return render(
                request,
                "job_seekers/partials/limit_reached.html",
                {"remaining_upgrades": 0},
                status=429,
            )

        profile = ProfileManager.get_profile_for_user(user)
        if profile is None:
            return HttpResponseBadRequest("Profile not found.")

        linkedin_markdown: str = optimize_linkedin_content(
            cast(JobSeekerProfile, profile)
        )

        # Cache for potential future use (not strictly required)
        request.session["optimized_linkedin_markdown"] = linkedin_markdown

        sections = parse_linkedin_markdown(linkedin_markdown)

        return render(
            request,
            "job_seekers/partials/optimized_linkedin.html",
            {
                "headline": sections.get("headline", ""),
                "about": sections.get("about", ""),
                "remaining_generations": max(LINKEDIN_DAILY_LIMIT - current_usage, 0),
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


class ApplyUpgradedResumeView(
    LoginRequiredMixin, ProfileAccessMixin, HTMXViewMixin, View
):
    """Kick off the *full* resume-ingestion pipeline using the upgraded markdown.

    This implementation mirrors the behaviour of :class:`ResumeUploadView` so
    that the upgraded document travels through the exact same extraction → XML
    conversion → profile-update flow as a regular file upload. Doing so keeps
    all downstream features (tagline generation, talent-pool handling, etc.)
    intact.
    """

    def post(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:  # noqa: C901 – complexity comparable to upload view
        # ------------------------------------------------------------------
        # Retrieve the upgraded markdown that was cached in the session after
        # the initial LLM call.
        # ------------------------------------------------------------------
        resume_md: str | None = request.session.get("upgraded_resume_markdown")
        if not resume_md:
            return HttpResponseBadRequest("No upgraded resume data found in session.")

        # ------------------------------------------------------------------
        # Validate access and look up the job-seeker profile (create if needed
        # – parity with ResumeUploadView).
        # ------------------------------------------------------------------
        user = cast(AuthenticatedUser, request.user)

        # Ensure user is a job-seeker
        error_response = self.ensure_job_seeker(request)
        if error_response:
            return error_response

        user_model = cast(User, user)  # explicit cast for typing clarity

        # Ensure a JobSeekerProfile exists
        job_seeker_profile = ProfileManager.get_profile_for_user(user_model)
        if job_seeker_profile is None:
            # Lazily create one to match upload behaviour
            job_seeker_profile = JobSeekerProfile.objects.create(user_owner=user_model)

        profile_id = getattr(job_seeker_profile, "pk", None)
        if profile_id is None:
            return HttpResponseBadRequest("Unable to resolve profile ID.")

        # ------------------------------------------------------------------
        # Immediately withdraw from the talent pool and delete any outdated
        # talent sheet – this mirrors ResumeUploadView safeguarding steps.
        # ------------------------------------------------------------------
        TalentPoolManager.toggle_talent_pool(user_model, join=False)
        TalentSheet.objects.filter(job_seeker=job_seeker_profile).delete()

        # ------------------------------------------------------------------
        # Persist the markdown to storage as a temporary text file so that the
        # existing Celery pipeline, which expects a *file path*, can operate
        # unchanged.
        # ------------------------------------------------------------------
        unique_filename = f"{uuid4()}_upgraded_resume.txt"
        file_path = default_storage.save(
            f"resumes/{unique_filename}", ContentFile(resume_md.encode("utf-8"))
        )

        # ------------------------------------------------------------------
        # Create a task-tracking row and queue the Celery chain identical to
        # the regular upload flow.
        # ------------------------------------------------------------------
        timestamp = int(time.time())
        task_id = f"resume_processing_{profile_id}_{timestamp}"

        task_progress = ResumeProcessor.create_processing_task(user_model, task_id)

        task_chain = chain(
            handle_resume_upload_task.si(  # type: ignore[misc]
                file_path, profile_id, task_id=task_progress.task_id
            ),
            resume_processing_completed.s(),  # type: ignore[misc]
        )

        task_chain.apply_async()  # Fire-and-forget – actual status is polled

        # Mark first pipeline step as complete (parity with upload view)
        ResumeProcessor.update_task_progress(
            task_progress.task_id,
            "file_path_resolved",
            "Resume file saved and ready for processing",
        )

        # ------------------------------------------------------------------
        # Build status/redirect URLs so the front-end progress widget can poll
        # the task and eventually transition the user back to their profile.
        # ------------------------------------------------------------------
        status_url = reverse(
            "job_seekers:task_status", kwargs={"task_id": task_progress.task_id}
        )

        # ------------------------------------------------------------------
        # HTMX request → return the processing widget so the current page can
        # display the progress popup. Non-HTMX callers (unlikely from the UI)
        # fall back to JSON for completeness.
        # ------------------------------------------------------------------
        is_htmx = self.is_htmx_request(request)

        if is_htmx:
            progress_info: dict[str, Any] = cast(
                dict[str, Any], task_progress.to_dict()
            )
            steps_list = progress_info.get("steps", [])  # type: ignore[call-arg]
            progress_percent = progress_info.get("progress_percent", 0)  # type: ignore[call-arg]
            current_step_name = progress_info.get("current_step_name", "Processing...")  # type: ignore[call-arg]
            current_step_desc = progress_info.get("current_step_description", "")  # type: ignore[call-arg]

            return render(
                request,
                "job_seekers/partials/processing.html",
                {
                    "task_id": task_progress.task_id,
                    "status_url": status_url,
                    "steps": steps_list,
                    "progress_percent": progress_percent,
                    "current_step_name": current_step_name,
                    "current_step_description": current_step_desc,
                },
                status=202,
            )

        # Fallback: API/postman – return JSON
        return JsonResponse(
            {
                "success": True,
                "message": "Resume queued for processing.",
                "task_id": task_progress.task_id,
                "status_url": status_url,
            },
            status=202,
        )
