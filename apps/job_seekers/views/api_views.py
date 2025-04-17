"""API views for job seekers."""

import json
import logging
from typing import cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, HttpResponseBase, JsonResponse
from django.views import View

from apps.authentication.types import AuthenticatedUser
from apps.job_seekers.services import ProfileManager, TalentPoolManager
from apps.job_seekers.views.mixins import HTMXViewMixin, ProfileAccessMixin

# Setup logging
logger = logging.getLogger(__name__)


class PersonalTaglineView(LoginRequiredMixin, ProfileAccessMixin, HTMXViewMixin, View):
    """API view to retrieve the personal tagline for a job seeker."""

    def get(self, request: HttpRequest) -> HttpResponseBase:
        """
        Get the personal tagline for the authenticated job seeker.

        Returns:
            HttpResponse: Either HTML for HTMX requests or JSON for API requests
        """
        user = cast(AuthenticatedUser, request.user)

        # Ensure user is a job seeker
        error_response = self.ensure_job_seeker(request)
        if error_response:
            return error_response

        # Get the user's profile
        profile = ProfileManager.get_profile_for_user(user)

        # Safely get the personal tagline
        tagline = getattr(profile, "personal_tagline", "") or ""

        # Check if request came from HTMX
        is_htmx = self.is_htmx_request(request)

        # If tagline is available and this is an HTMX request, return HTML
        if is_htmx:
            if tagline:
                # Return the tagline without spinner and use status code 286 to stop polling
                html = f"<span>{tagline}</span>"
                return HttpResponse(html, status=286)
            else:
                # Return the original content with spinner for HTMX
                html = """
                <span id="tagline-spinner" class="loading loading-spinner loading-xs mr-1"></span>
                <span>Job Seeker</span>
                """
                return HttpResponse(html)

        # For regular API requests, return JSON
        return JsonResponse({"personal_tagline": tagline})


class ToggleTalentPoolView(LoginRequiredMixin, ProfileAccessMixin, HTMXViewMixin, View):
    """API view to toggle a job seeker's talent pool status."""

    def post(self, request: HttpRequest) -> HttpResponseBase:
        """
        Toggle the job seeker's active status in the talent pool.

        Args:
            request: The HTTP request containing the desired active state

        Returns:
            JsonResponse: A JSON response indicating success or failure
        """
        user = cast(AuthenticatedUser, request.user)

        # Ensure user is a job seeker
        error_response = self.ensure_job_seeker(request)
        if error_response:
            return error_response

        try:
            # Parse the request body to get the active state
            data = json.loads(request.body)
            active = data.get("active", False)

            # Log the status change
            logger.info(
                "Job seeker %s %s the talent pool",
                user.email,
                "entered" if active else "left",
            )

            # Use the service to toggle talent pool status
            result = TalentPoolManager.toggle_talent_pool(user, join=active)

            if "error" in result:
                return JsonResponse(
                    {"success": False, "message": result["error"]}, status=404
                )

            return JsonResponse(
                {
                    "success": True,
                    "message": "Talent pool status updated successfully",
                    "in_talent_pool": result["in_talent_pool"],
                }
            )

        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "message": "Invalid JSON data"}, status=400
            )
        except Exception as e:
            logger.error("Error updating talent pool status: %s", str(e), exc_info=True)
            return JsonResponse(
                {"success": False, "message": f"Error: {str(e)}"}, status=500
            )


class ToggleRoleInterestView(
    LoginRequiredMixin, ProfileAccessMixin, HTMXViewMixin, View
):
    """API view to toggle a job seeker's interest in a role recommendation."""

    def post(self, request: HttpRequest, role_id: int) -> HttpResponseBase:
        """
        Toggle the job seeker's interest in a specific role recommendation.

        Args:
            request: The HTTP request
            role_id: The ID of the role recommendation to toggle interest for

        Returns:
            HttpResponse: HTML for the updated button or JSON response
        """
        user = cast(AuthenticatedUser, request.user)

        # Ensure user is a job seeker
        error_response = self.ensure_job_seeker(request)
        if error_response:
            return error_response

        # Get the user's profile
        profile = ProfileManager.get_profile_for_user(user)

        # Get the role recommendation
        try:
            # Parse action from the request body
            try:
                data = json.loads(request.body.decode("utf-8"))
                interested = data.get("interested", True)  # Default to showing interest
            except json.JSONDecodeError:
                interested = True  # Default action if no JSON is provided

            # Use the service to toggle role interest, passing the profile for authorization check
            updated_role = TalentPoolManager.toggle_role_interest(
                role_id, interested=interested, profile=profile
            )

            if updated_role is None:
                return self.render_htmx_or_json(
                    request,
                    "job_seekers/partials/error.html",
                    {
                        "success": False,
                        "message": "Role recommendation not found or unauthorized",
                    },
                    status=404,
                )

            # For HTMX requests, return updated button
            if self.is_htmx_request(request):
                if updated_role.is_candidate_interested:
                    # Button to remove interest
                    button_html = f"""
                    <button hx-post="/job-seekers/api/toggle-role-interest/{updated_role.pk}/" 
                            hx-headers='{{"Content-Type": "application/json"}}'
                            hx-swap="outerHTML"
                            hx-trigger="click"
                            hx-vals='{{"interested": false}}'
                            class="btn btn-sm btn-primary">
                        <span class="mr-1">✓</span> Interested
                    </button>
                    """
                else:
                    # Button to add interest
                    button_html = f"""
                    <button hx-post="/job-seekers/api/toggle-role-interest/{updated_role.pk}/"
                            hx-headers='{{"Content-Type": "application/json"}}'
                            hx-swap="outerHTML"
                            hx-trigger="click"
                            hx-vals='{{"interested": true}}'
                            class="btn btn-sm btn-outline">
                        <span class="mr-1">+</span> Show Interest
                    </button>
                    """
                # Add a special header to update the card class
                response = HttpResponse(button_html)

                # Trigger card class update via JavaScript
                js_trigger = {
                    "updateCardClass": {
                        "roleId": role_id,
                        "isInterested": updated_role.is_candidate_interested,
                    }
                }
                response.headers["HX-Trigger"] = json.dumps(js_trigger)

                return response
            else:
                # For API requests, return JSON with updated status
                return JsonResponse(
                    {
                        "success": True,
                        "role_id": updated_role.pk,
                        "is_interested": updated_role.is_candidate_interested,
                    }
                )

        except Exception as e:
            # Log the error
            logger.exception("Error toggling role interest: %s", str(e))

            # Return appropriate error response
            if self.is_htmx_request(request):
                return self.render_for_htmx(
                    request,
                    "job_seekers/partials/error.html",
                    {"message": f"Error: {str(e)}"},
                    status=500,
                )
            else:
                return JsonResponse({"error": str(e)}, status=500)


class TalentPoolStatusView(LoginRequiredMixin, ProfileAccessMixin, HTMXViewMixin, View):
    """API view to get the talent pool status for a job seeker."""

    def get(self, request: HttpRequest) -> HttpResponseBase:
        """
        Get the job seeker's talent pool status.

        Returns:
            JsonResponse: A JSON response with the talent pool status
        """
        user = cast(AuthenticatedUser, request.user)

        # Ensure user is a job seeker
        error_response = self.ensure_job_seeker(request)
        if error_response:
            return error_response

        # Use the service to get talent pool status
        status = TalentPoolManager.get_talent_pool_status(user)

        return JsonResponse(
            {
                "success": True,
                "in_talent_pool": status["in_talent_pool"],
                "has_talent_sheet": status["has_talent_sheet"],
                "is_published": status["is_published"],
            }
        )
