"""API views for job seekers."""

import json
import logging
from typing import Any, cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from apps.authentication.types import AuthenticatedUser

# Setup logging
logger = logging.getLogger(__name__)


class PersonalTaglineView(LoginRequiredMixin, View):
    """API view to retrieve the personal tagline for a job seeker."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """
        Get the personal tagline for the authenticated job seeker.

        Returns:
            HttpResponse: Either HTML for HTMX requests or JSON for API requests
        """
        user = cast(AuthenticatedUser, request.user)

        # Ensure user is a job seeker
        if user.user_type != "job_seeker":
            return JsonResponse({"error": "User is not a job seeker"}, status=403)

        # Get the job seeker's profile
        if not hasattr(user, "job_seeker_profile"):
            return JsonResponse({"error": "Job seeker profile not found"}, status=404)

        profile = user.job_seeker_profile

        # Safely get the personal tagline
        tagline = getattr(profile, "personal_tagline", "") or ""

        # Check if request came from HTMX
        is_htmx = "HX-Request" in request.headers

        # If tagline is available and this is an HTMX request, return HTML
        if is_htmx:
            if tagline:
                # Return the tagline without the spinner for HTMX
                html = f"<span>{tagline}</span>"

                # Stop further polling by adding HX-Reswap header
                response = HttpResponse(html)
                response.headers["HX-Reswap"] = "innerHTML"
                response.headers["HX-Trigger"] = "taglineLoaded"

                # Add a special header to stop the polling
                response.headers["HX-Trigger-After-Swap"] = (
                    '{"stopPolling": {"target": "#tagline-container"}}'
                )
                return response
            else:
                # Return the original content with spinner for HTMX
                html = """
                <span id="tagline-spinner" class="loading loading-spinner loading-xs mr-1"></span>
                <span>Job Seeker</span>
                """
                return HttpResponse(html)

        # For regular API requests, return JSON
        return JsonResponse({"personal_tagline": tagline})
