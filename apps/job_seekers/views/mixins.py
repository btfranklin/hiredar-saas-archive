"""
Mixins for job_seekers views.

These mixins provide reusable functionality across multiple views.
"""

from typing import Any, cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, HttpResponseBase, JsonResponse
from django.shortcuts import redirect, render

from apps.authentication.types import AuthenticatedUser
from apps.job_seekers.services import ProfileManager


class HTMXViewMixin:
    """
    Mixin for views that handle both HTMX and regular requests.

    This mixin provides helper methods to differentiate between HTMX requests
    and regular requests, and to render appropriate responses.
    """

    def is_htmx_request(self, request: HttpRequest) -> bool:
        """Check if the request is an HTMX request."""
        return "HX-Request" in request.headers

    def render_for_htmx(
        self,
        request: HttpRequest,
        template_name: str,
        context: dict[str, Any] | None = None,
        status: int = 200,
    ) -> HttpResponse:
        """Render an HTML response for HTMX requests."""
        context = context or {}
        return render(request, template_name, context, status=status)

    def render_htmx_or_json(
        self,
        request: HttpRequest,
        htmx_template: str,
        json_data: dict[str, Any],
        context: dict[str, Any] | None = None,
        status: int = 200,
    ) -> HttpResponse:
        """
        Render an HTML response for HTMX requests, or JSON for API requests.

        Args:
            request: The HTTP request
            htmx_template: Template to render for HTMX requests
            json_data: Data to return as JSON for non-HTMX requests
            context: Additional context for the template (will be merged with json_data)
            status: HTTP status code

        Returns:
            Either a rendered template or JSON response based on request type
        """
        if self.is_htmx_request(request):
            # For HTMX requests, render template
            template_context = {**json_data, **(context or {})}
            return self.render_for_htmx(
                request, htmx_template, template_context, status
            )
        else:
            # For non-HTMX requests, return JSON
            return JsonResponse(json_data, status=status)


class ProfileAccessMixin:
    """
    Mixin for ensuring a user has access to job seeker functionality.

    This mixin checks that the user is a job seeker and handles access control.
    """

    def ensure_job_seeker(
        self, request: HttpRequest
    ) -> HttpResponse | JsonResponse | None:
        """
        Ensure the user is a job seeker.

        Returns None if the user is a job seeker, otherwise returns an appropriate
        error response.
        """
        if getattr(request.user, "user_type", None) != "job_seeker":
            if "HX-Request" in request.headers:
                return render(
                    request,
                    "job_seekers/partials/error.html",
                    {"message": "Only job seekers can access this functionality."},
                    status=403,
                )
            else:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Only job seekers can access this functionality.",
                    },
                    status=403,
                )


class JobSeekerRequiredMixin(LoginRequiredMixin):
    """Mixin that restricts access to authenticated *job-seeker* users only.

    It combines the standard login check with two additional guards:
    1. ``user.user_type`` must equal ``"job_seeker"``.
    2. A related ``JobSeekerProfile`` must already exist; if not, the user
       is redirected to the profile-creation flow.
    """

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:  # type: ignore[override]
        # Let ``LoginRequiredMixin`` short-circuit unauthenticated users.
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        user = cast(AuthenticatedUser, request.user)

        # Ensure the authenticated user is actually a job seeker.
        if getattr(user, "user_type", None) != "job_seeker":
            return redirect("core:home")

        # Ensure the job-seeker profile exists; otherwise, send them to create it.
        try:
            ProfileManager.get_profile_for_user(user)
        except Exception:  # Broad but fine: we redirect on *any* lookup failure.
            return redirect("job_seekers:profile_create")

        # All checks passed – continue with normal dispatch chain.
        return super().dispatch(request, *args, **kwargs)
