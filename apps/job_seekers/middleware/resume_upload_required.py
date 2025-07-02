"""Middleware to require resume upload for job-seekers.

If an authenticated user with ``user_type == "job_seeker"`` has **no** resume
attached to their primary `JobSeekerProfile`, redirect them to the resume
upload page and block access to the rest of the application.

The following URLs remain accessible so the user can successfully upload their
resume and track processing progress:

* ``job_seekers:profile_create`` – page containing the upload form
* ``job_seekers:resume_upload`` – POST endpoint that receives the actual file
* ``job_seekers:task_status`` – polling endpoint used whilst the resume is being
  processed (prefix-match)

Static and media assets as well as the logout URL are also excluded.
"""

from __future__ import annotations

from typing import Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

# Pattern to match the task-status endpoint regardless of the ``task_id``
TASK_STATUS_PREFIX = reverse(
    "job_seekers:task_status", kwargs={"task_id": "___"}
).rsplit("___/", 1)[0]


class ResumeUploadRequiredMiddleware(MiddlewareMixin):
    """Force job-seekers to upload a resume before using the site."""

    #: Exact URL paths that remain accessible while the user still needs to upload
    #: a resume.  Populated during ``__init__`` when URL routing is available.
    _EXEMPT_PATHS: set[str]

    #: Path prefixes that should bypass the check (contain dynamic segments)
    _EXEMPT_PREFIXES: tuple[str, ...]

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        super().__init__(get_response)

        # Build list of exempt *exact* paths
        self._EXEMPT_PATHS = {
            reverse("job_seekers:profile_create"),
            reverse("job_seekers:resume_upload"),
        }

        # Include the logout URL if available (depends on allauth / custom config)
        try:
            self._EXEMPT_PATHS.add(reverse("account_logout"))  # type: ignore[arg-type]
        except Exception:
            pass

        # Prefixes (for dynamic URL segments)
        self._EXEMPT_PREFIXES = (
            TASK_STATUS_PREFIX,
            "/static/",
            "/media/",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _path_is_exempt(self, path: str) -> bool:
        """Return *True* if *path* should bypass the resume-upload check."""

        if path in self._EXEMPT_PATHS:
            return True
        return any(path.startswith(prefix) for prefix in self._EXEMPT_PREFIXES)

    # ------------------------------------------------------------------
    # Django middleware API
    # ------------------------------------------------------------------

    def process_request(self, request: HttpRequest) -> HttpResponse | None:  # type: ignore[override]
        """Redirect job-seekers without a resume to the upload page."""

        user = getattr(request, "user", None)
        if not getattr(user, "is_authenticated", False):
            return None  # anonymous – ignore

        if getattr(user, "user_type", None) != "job_seeker":
            return None  # recruiters / admins unaffected

        # Skip when already on an exempt URL (upload flow, static assets, etc.)
        if self._path_is_exempt(request.path):
            return None

        # Lazy import to avoid AppRegistryNotReady at start-up
        from apps.job_seekers.models import (
            JobSeekerProfile,  # noqa: WPS433 – internal import intentional
        )

        # Try to get cached profile (set elsewhere during the request)
        profile: "JobSeekerProfile | None" = getattr(user, "job_seeker_profile", None)

        # Fallback to DB lookup if not already attached
        if profile is None:
            try:
                profile = (
                    JobSeekerProfile.objects.filter(user_owner=user)
                    .only("resume_xml")
                    .first()
                )
            except Exception:
                profile = None

            if profile is not None:
                setattr(user, "job_seeker_profile", profile)

        # Block access when no profile or resume yet
        if profile is None or not profile.resume_xml:
            return redirect(reverse("job_seekers:profile_create"))

        # Everything OK – continue processing
        return None
