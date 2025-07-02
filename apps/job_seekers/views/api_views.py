"""API views for job seekers."""

import json
import logging
from typing import cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, HttpResponseBase, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views import View

from apps.authentication.types import AuthenticatedUser
from apps.job_seekers.models import RoleRecommendation
from apps.job_seekers.services import ProfileManager, TalentPoolManager
from apps.job_seekers.views.mixins import HTMXViewMixin, ProfileAccessMixin

# Setup logging
logger = logging.getLogger(__name__)


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

        # Get the role recommendation and determine new interest state
        role = get_object_or_404(RoleRecommendation, id=role_id)
        new_interest_state = not role.is_candidate_interested

        # Use the service to toggle role interest to the opposite of current
        updated_role = TalentPoolManager.toggle_role_interest(
            role_id, interested=new_interest_state, profile=profile
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

        if self.is_htmx_request(request):
            # Re-render the recommended roles section and return it for swapping
            # Recompute role lists for current profile
            interested_roles = RoleRecommendation.objects.filter(
                job_seeker=profile,
                is_candidate_interested=True,
            ).order_by("role_title")[:5]

            other_roles = RoleRecommendation.objects.filter(
                job_seeker=profile,
                is_candidate_interested=False,
            ).order_by("role_title")[:5]

            html = render_to_string(
                "job_seekers/partials/recommended_roles.html",
                {
                    "interested_roles": interested_roles,
                    "other_roles": other_roles,
                },
                request=request,
            )

            return HttpResponse(html)
        else:
            # For API requests, return JSON with updated status
            return JsonResponse(
                {
                    "success": True,
                    "role_id": updated_role.pk,
                    "is_interested": updated_role.is_candidate_interested,
                }
            )


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
