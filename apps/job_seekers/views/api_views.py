"""API views for job seekers."""

import json
import logging
from typing import cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from apps.authentication.types import AuthenticatedUser
from apps.job_seekers.models import RoleRecommendation

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


class ToggleRoleInterestView(LoginRequiredMixin, View):
    """API view to toggle a job seeker's interest in a role recommendation."""

    def post(self, request: HttpRequest, role_id: int) -> HttpResponse:
        """
        Toggle the job seeker's interest in a specific role recommendation.

        Args:
            request: The HTTP request
            role_id: The ID of the role recommendation to toggle interest for

        Returns:
            HttpResponse: HTML for the updated button
        """
        user = cast(AuthenticatedUser, request.user)

        # Ensure user is a job seeker
        if user.user_type != "job_seeker":
            return HttpResponse("Unauthorized", status=403)

        # Get the job seeker's profile
        if not hasattr(user, "job_seeker_profile"):
            return HttpResponse("Profile not found", status=404)

        profile = user.job_seeker_profile

        # Get the role recommendation and check if it belongs to this job seeker
        role = get_object_or_404(RoleRecommendation, id=role_id)

        if role.job_seeker != profile:
            return HttpResponse("Unauthorized", status=403)

        # Toggle the interest flag
        role.is_candidate_interested = not role.is_candidate_interested
        role.save(update_fields=["is_candidate_interested"])

        # Return the updated button HTML
        if role.is_candidate_interested:
            button_html = """
            <button class="btn btn-sm interest-btn btn-success"
                    hx-post="{}"
                    hx-swap="outerHTML"
                    hx-target="closest .interest-btn">
                <i class="fas fa-check mr-2"></i> Interested
            </button>
            """.format(
                request.path
            )
        else:
            button_html = """
            <button class="btn btn-sm interest-btn btn-primary"
                    hx-post="{}"
                    hx-swap="outerHTML"
                    hx-target="closest .interest-btn">
                <i class="fas fa-thumbs-up mr-2"></i> I'm Interested
            </button>
            """.format(
                request.path
            )

        # Add a special header to update the card class
        response = HttpResponse(button_html)

        # Trigger card class update via JavaScript
        js_trigger = {
            "updateCardClass": {
                "roleId": role_id,
                "isInterested": role.is_candidate_interested,
            }
        }
        response.headers["HX-Trigger"] = json.dumps(js_trigger)

        return response
