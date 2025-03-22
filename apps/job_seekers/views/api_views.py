"""API views for job seekers."""

import json
import logging
from typing import cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django_q.tasks import async_task

from apps.authentication.types import AuthenticatedUser
from apps.job_seekers.models import RoleRecommendation, TalentSheet
from apps.job_seekers.tasks.talent_sheet_tasks import generate_talent_sheet_task

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


class ToggleTalentPoolView(LoginRequiredMixin, View):
    """API view to toggle a job seeker's talent pool status."""

    def post(self, request: HttpRequest) -> JsonResponse:
        """
        Toggle the job seeker's active status in the talent pool.

        Args:
            request: The HTTP request containing the desired active state

        Returns:
            JsonResponse: A JSON response indicating success or failure
        """
        user = cast(AuthenticatedUser, request.user)

        # Ensure user is a job seeker
        if user.user_type != "job_seeker":
            return JsonResponse(
                {"success": False, "message": "User is not a job seeker"}, status=403
            )

        # Get the job seeker's profile
        if not hasattr(user, "job_seeker_profile"):
            return JsonResponse(
                {"success": False, "message": "Job seeker profile not found"},
                status=404,
            )

        profile = user.job_seeker_profile
        if profile is None:
            return JsonResponse(
                {"success": False, "message": "Job seeker profile is None"},
                status=404,
            )

        try:
            # Parse the request body to get the active state
            data = json.loads(request.body)
            active = data.get("active", False)

            # Log the status change
            profile_id = getattr(profile, "id", "unknown")
            logger.info(
                "Job seeker %s (ID: %s) %s the talent pool",
                user.email,
                profile_id,
                "entered" if active else "left",
            )

            # If the job seeker is entering the talent pool, schedule a task to generate their talent sheet
            if active:
                try:
                    # Schedule the talent sheet generation task
                    task_id = async_task(
                        generate_talent_sheet_task,
                        getattr(profile, "id"),
                        hook=None,  # No callback needed
                        task_name=f"generate_talent_sheet_{getattr(profile, 'id')}",
                    )

                    logger.info(
                        "Scheduled talent sheet generation task (ID: %s) for job seeker %s",
                        task_id,
                        user.email,
                    )
                except Exception as e:
                    # Log the error but don't fail the request
                    logger.error(
                        "Error scheduling talent sheet generation task: %s",
                        str(e),
                        exc_info=True,
                    )
            # If the job seeker is leaving the talent pool, unpublish their talent sheet
            else:
                try:
                    # Find and unpublish the talent sheet if it exists
                    talent_sheet = TalentSheet.objects.filter(
                        job_seeker=profile
                    ).first()
                    if talent_sheet:
                        talent_sheet.is_published = False
                        talent_sheet.save(update_fields=["is_published"])
                        logger.info(
                            "Unpublished talent sheet for job seeker %s leaving talent pool",
                            user.email,
                        )
                except Exception as e:
                    # Log the error but don't fail the request
                    logger.error(
                        "Error unpublishing talent sheet: %s",
                        str(e),
                        exc_info=True,
                    )

            return JsonResponse(
                {
                    "success": True,
                    "message": "Talent pool status updated successfully",
                    "in_talent_pool": profile.in_talent_pool,
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
        if profile is None:
            return HttpResponse("Profile is None", status=404)

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
