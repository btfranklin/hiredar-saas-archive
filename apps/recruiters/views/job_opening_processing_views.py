"""
Job opening processing views for the recruiters app.

This module contains views for processing text job descriptions and
tracking the status of job opening creation tasks.
"""

import logging
import uuid

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import View

from apps.core.tasks import safe_async_task
from apps.recruiters.models import JobOpeningProcessingTask, RecruiterProfile

# Setup logging
logger = logging.getLogger(__name__)

# Alias safe_async_task as async_task
async_task = safe_async_task


class TextProcessJobOpeningView(LoginRequiredMixin, UserPassesTestMixin, View):
    """View for processing a text job description and creating a job opening."""

    def test_func(self) -> bool:
        """Verify the user is a recruiter."""
        return getattr(self.request.user, "user_type", "") == "recruiter"

    def post(self, request: HttpRequest) -> HttpResponse:
        """Process the text job description and queue an async task."""
        # Check if this is an AJAX request for consistent error handling
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        try:
            job_title = request.POST.get("job_title", "").strip()
            job_description = request.POST.get("job_description", "").strip()

            if not job_title or not job_description:
                if is_ajax:
                    response = JsonResponse(
                        {
                            "success": False,
                            "message": "Please provide both a job title and description.",
                        },
                        status=400,
                    )
                    response["Content-Type"] = "application/json"
                    return response
                messages.error(
                    request, "Please provide both a job title and description."
                )
                return redirect("recruiters:job_openings_create")

            # Get the recruiter profile
            try:
                recruiter_profile = RecruiterProfile.objects.get(user=request.user)
            except RecruiterProfile.DoesNotExist:
                error_msg = "Recruiter profile not found for current user."
                logger.error(error_msg)
                if is_ajax:
                    response = JsonResponse(
                        {"success": False, "message": error_msg}, status=400
                    )
                    response["Content-Type"] = "application/json"
                    return response
                messages.error(request, error_msg)
                return redirect("recruiters:job_openings_create")

            # Create a unique task ID
            task_id = str(uuid.uuid4())

            # Create a new processing task
            task = JobOpeningProcessingTask.objects.create(
                task_id=task_id,
                recruiter=recruiter_profile,
                job_title=job_title,
                original_text=job_description,
                status="pending",
                current_step="Initializing",
                progress_percent=0,
            )

            # Queue the async task to process the job description
            async_task(
                "apps.recruiters.tasks.handle_job_description_task",
                task.task_id,  # Use task object reference
                task.job_title,
                task.original_text,
                recruiter_profile.pk,
                hook="apps.recruiters.tasks.hooks.job_processing_done",
            )

            # Handle AJAX/HTMX requests
            if is_ajax:
                status_url = reverse(
                    "recruiters:job_openings_process_status",
                    kwargs={"task_id": task.task_id},
                )
                redirect_url = reverse("recruiters:job_openings_list")

                response = JsonResponse(
                    {
                        "success": True,
                        "message": "Job description submitted. Processing in progress.",
                        "task_id": task.task_id,
                        "status_url": status_url,
                        "redirect_url": redirect_url,
                    }
                )
                # Force the Content-Type to be application/json to prevent middleware from changing it
                response["Content-Type"] = "application/json"
                # Add a custom header to track if this response gets modified
                response["X-Hiredar-Response-Type"] = "json"
                return response

            # Redirect to the processing status page for non-AJAX requests
            return redirect(
                "recruiters:job_openings_process_status", task_id=task.task_id
            )

        except Exception as e:
            # Log the error
            error_msg = f"Error processing job description: {str(e)}"
            logger.exception(error_msg)

            # Return appropriate response based on request type
            if is_ajax:
                response = JsonResponse(
                    {"success": False, "message": error_msg}, status=500
                )
                response["Content-Type"] = "application/json"
                return response

            messages.error(
                request,
                "An error occurred while processing your request. Please try again.",
            )
            return redirect("recruiters:job_openings_create")


class JobOpeningTaskStatusView(LoginRequiredMixin, UserPassesTestMixin, View):
    """View for checking the status of a job opening processing task."""

    def test_func(self) -> bool:
        """Verify the user is a recruiter."""
        return getattr(self.request.user, "user_type", "") == "recruiter"

    def get(self, request: HttpRequest, task_id: str) -> HttpResponse:
        """
        Return JSON status for AJAX requests or redirect for direct browser requests.
        """
        # Check if this is an AJAX request
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        # For direct browser requests, redirect to the create page
        if not is_ajax:
            return redirect("recruiters:job_openings_create")

        # For AJAX requests, return JSON status
        try:
            task = JobOpeningProcessingTask.objects.get(
                task_id=task_id,
                recruiter__user=request.user,
            )
            response = JsonResponse(task.to_dict())
            # Force the Content-Type to be application/json to prevent middleware from changing it
            response["Content-Type"] = "application/json"
            return response
        except JobOpeningProcessingTask.DoesNotExist:
            logger.warning("Task not found: %s for user %s", task_id, request.user.pk)
            response = JsonResponse(
                {
                    "status": "error",
                    "message": "Task not found",
                    "progress_percent": 0,
                    "current_step": "Error",
                },
                status=404,
            )
            response["Content-Type"] = "application/json"
            return response
        except Exception as e:
            logger.exception("Error retrieving task status: %s", str(e))
            response = JsonResponse(
                {
                    "status": "error",
                    "message": f"Error retrieving task: {str(e)}",
                    "progress_percent": 0,
                    "current_step": "Error",
                },
                status=500,
            )
            response["Content-Type"] = "application/json"
            return response
