"""Resume processing views for job seekers."""

import logging
import uuid
from typing import Any, cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, HttpResponseBase, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import TemplateView, View
from django_q.tasks import async_task, result

from apps.authentication.types import AuthenticatedUser
from apps.job_seekers.models import ResumeProcessingTaskProgress
from apps.job_seekers.tasks import handle_resume_upload_task, save_resume_file

# Configure logging
logger = logging.getLogger(__name__)


class ProfileCreateView(LoginRequiredMixin, TemplateView):
    """Profile creation view for job seekers."""

    template_name = "job_seekers/profile_create.html"

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """Ensure only job seekers can access this view."""
        user = cast(AuthenticatedUser, request.user)
        if user.user_type != "job_seeker":
            return redirect("core:home")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add extra context data."""
        context = super().get_context_data(**kwargs)
        # Hide the user menu in the navbar for this page
        context["hide_user_menu"] = True
        return context


class ResumeUploadView(LoginRequiredMixin, View):
    """
    View for handling resume uploads from job seekers.

    This view accepts resume file uploads, saves them to the media directory,
    and queues an asynchronous task to process the resume and update the profile.
    """

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """Handle POST requests for resume uploads."""
        user = cast(AuthenticatedUser, request.user)
        is_htmx = "HX-Request" in request.headers

        logger.info("Resume upload request received - HTMX: %s", is_htmx)

        # Ensure user is a job seeker
        if user.user_type != "job_seeker":
            if is_htmx:
                # Return error template for HTMX requests
                return render(
                    request,
                    "job_seekers/partials/error.html",
                    {"message": "Only job seekers can upload resumes."},
                    status=403,
                )
            else:
                # Return JSON for non-HTMX requests (e.g., API clients)
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Only job seekers can upload resumes.",
                    },
                    status=403,
                )

        # Get the uploaded file
        resume_file = request.FILES.get("resume")
        if not resume_file:
            if is_htmx:
                return render(
                    request,
                    "job_seekers/partials/error.html",
                    {"message": "No resume file provided."},
                    status=400,
                )
            else:
                return JsonResponse(
                    {"success": False, "message": "No resume file provided."},
                    status=400,
                )

        # Validate file type (PDF only)
        filename = getattr(resume_file, "name", "")
        if not filename.lower().endswith(".pdf"):
            if is_htmx:
                return render(
                    request,
                    "job_seekers/partials/error.html",
                    {"message": "Only PDF files are accepted."},
                    status=400,
                )
            else:
                return JsonResponse(
                    {"success": False, "message": "Only PDF files are accepted."},
                    status=400,
                )

        try:
            logger.info("Processing upload for file: %s", filename)

            # Generate a unique filename
            unique_filename = f"{uuid.uuid4()}_{filename}"

            # Save the file
            file_path = save_resume_file(resume_file, unique_filename)

            # Get job seeker profile ID
            job_seeker_profile = getattr(user, "job_seeker_profile", None)
            if job_seeker_profile is None:
                if is_htmx:
                    return render(
                        request,
                        "job_seekers/partials/error.html",
                        {"message": "Job seeker profile not found."},
                        status=400,
                    )
                else:
                    return JsonResponse(
                        {"success": False, "message": "Job seeker profile not found."},
                        status=400,
                    )

            profile_id = job_seeker_profile.pk

            # Generate a unique ID for the task
            task_id = str(uuid.uuid4())
            logger.info("Created task ID: %s", task_id)

            # Create a tracking record for this task
            task_progress = ResumeProcessingTaskProgress.objects.create(
                task_id=task_id,
                user=user,
                task_type="resume_processing",
                status="pending",
                message="Preparing to process resume",
                current_step="file_path_resolved",
                progress_percent=0,
            )

            # Queue the resume processing task with a completion hook
            async_task(
                handle_resume_upload_task,
                file_path,
                profile_id,
                task_id=task_progress.task_id,
                task_name=f"resume_processing_{task_progress.task_id}",
                hook="apps.job_seekers.tasks.hooks.resume_processing_completed",
            )

            # Generate URLs for status checking and redirection
            status_url = reverse(
                "job_seekers:task_status", kwargs={"task_id": task_progress.task_id}
            )
            redirect_url = reverse("job_seekers:dashboard")

            logger.info("Task queued successfully, status URL: %s", status_url)

            if is_htmx:
                # For HTMX requests, return processing template
                # Get initial steps data for the template
                progress_data = task_progress.to_dict()
                logger.info("Returning processing template for HTMX request")

                return render(
                    request,
                    "job_seekers/partials/processing.html",
                    {
                        "task_id": task_progress.task_id,
                        "status_url": status_url,
                        "redirect_url": redirect_url,
                        "steps": progress_data.get("steps", []),
                        "progress_percent": progress_data.get("progress_percent", 0),
                        "current_step_name": progress_data.get(
                            "current_step_name", "Processing..."
                        ),
                        "current_step_description": progress_data.get(
                            "current_step_description", ""
                        ),
                    },
                )
            else:
                # For non-HTMX requests (like API calls), return JSON
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Resume uploaded successfully. Processing in progress.",
                        "task_id": task_progress.task_id,
                        "status_url": status_url,
                        "redirect_url": redirect_url,
                    }
                )

        except Exception as e:
            logger.exception("Error in resume upload: %s", str(e))
            if is_htmx:
                return render(
                    request,
                    "job_seekers/partials/error.html",
                    {"message": f"Error uploading resume: {str(e)}"},
                    status=500,
                )
            else:
                return JsonResponse(
                    {"success": False, "message": f"Error uploading resume: {str(e)}"},
                    status=500,
                )


class ResumeProcessingTaskProgressView(LoginRequiredMixin, View):
    """
    View for checking the status of asynchronous resume processing tasks.

    This view returns the current status of a task by its ID, either as JSON or HTML,
    depending on whether the request is an HTMX request.
    """

    def get(
        self, request: HttpRequest, task_id: str, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """Get the status of a task by its ID."""
        user = cast(AuthenticatedUser, request.user)

        # Ensure user is a job seeker
        if user.user_type != "job_seeker":
            if request.headers.get("HX-Request"):
                return render(
                    request,
                    "job_seekers/partials/error.html",
                    {"message": "Unauthorized"},
                    status=403,
                )
            else:
                return JsonResponse(
                    {"success": False, "message": "Unauthorized"}, status=403
                )

        try:
            # First check the TaskProgress model for detailed progress information
            try:
                task_progress = ResumeProcessingTaskProgress.objects.get(
                    task_id=task_id, user=user
                )

                progress_data = task_progress.to_dict()

                # Check if task completed or failed
                if task_progress.status == "completed":
                    if request.headers.get("HX-Request"):
                        # Redirect to dashboard using HTMX response headers
                        redirect_url = reverse("job_seekers:dashboard")
                        response = HttpResponse(
                            "<div>Processing complete! Redirecting...</div>"
                        )
                        response["HX-Redirect"] = redirect_url
                        return response
                    else:
                        return JsonResponse(
                            {
                                "success": True,
                                "status": "completed",
                                "message": task_progress.message,
                                "redirect_url": reverse("job_seekers:dashboard"),
                            }
                        )

                elif task_progress.status == "failed":
                    if request.headers.get("HX-Request"):
                        return render(
                            request,
                            "job_seekers/partials/error.html",
                            {
                                "message": task_progress.message
                                or "Task processing failed"
                            },
                            status=200,
                        )
                    else:
                        return JsonResponse(
                            {
                                "success": False,
                                "status": "failed",
                                "message": task_progress.message,
                            }
                        )

                # Task is still in progress
                if request.headers.get("HX-Request"):
                    # Return the processing template with updated progress
                    context = {
                        "status_url": reverse(
                            "job_seekers:task_status", kwargs={"task_id": task_id}
                        ),
                        "redirect_url": reverse("job_seekers:dashboard"),
                        "steps": progress_data.get("steps", []),
                        "progress_percent": progress_data.get("progress_percent", 0),
                        "current_step_name": progress_data.get(
                            "current_step_name", "Processing..."
                        ),
                        "current_step_description": progress_data.get(
                            "current_step_description", ""
                        ),
                    }
                    return render(
                        request, "job_seekers/partials/processing.html", context
                    )
                else:
                    # Return JSON for API clients
                    return JsonResponse(
                        {
                            "success": True,
                            "status": task_progress.status,
                            "message": task_progress.message,
                            "progress": progress_data,
                        }
                    )

            except ResumeProcessingTaskProgress.DoesNotExist:
                # Fall back to checking Django Q2 result
                pass

            # Get the task result from Django Q2
            task_result = result(task_id)

            if task_result is None:
                # Task is still running but we don't have progress data
                if request.headers.get("HX-Request"):
                    # Return a simple processing state
                    context = {
                        "status_url": reverse(
                            "job_seekers:task_status", kwargs={"task_id": task_id}
                        ),
                        "redirect_url": reverse("job_seekers:dashboard"),
                        "steps": [],
                        "progress_percent": -1,  # Indeterminate progress
                        "current_step_name": "Processing Resume",
                        "current_step_description": "Your resume is being processed...",
                    }
                    return render(
                        request, "job_seekers/partials/processing.html", context
                    )
                else:
                    # Return JSON for API clients
                    return JsonResponse(
                        {
                            "success": True,
                            "status": "running",
                            "message": "Task is still running",
                            "progress": {
                                "progress_percent": -1,  # Use -1 to indicate indeterminate progress
                                "current_step": "processing",
                                "current_step_name": "Processing Resume",
                                "steps": [],
                            },
                        }
                    )

            # Task has completed (might be success or error)
            if task_result.get("status", "error") == "success":
                if request.headers.get("HX-Request"):
                    # Redirect to dashboard using HTMX response headers
                    redirect_url = reverse("job_seekers:dashboard")
                    response = HttpResponse(
                        "<div>Processing complete! Redirecting...</div>"
                    )
                    response["HX-Redirect"] = redirect_url
                    return response
                else:
                    return JsonResponse(
                        {
                            "success": True,
                            "status": "completed",
                            "message": task_result.get("message", ""),
                            "profile_data": task_result.get("profile_data", {}),
                            "redirect_url": reverse("job_seekers:dashboard"),
                        }
                    )
            else:
                # Task failed
                if request.headers.get("HX-Request"):
                    return render(
                        request,
                        "job_seekers/partials/error.html",
                        {
                            "message": task_result.get(
                                "message", "Task processing failed"
                            )
                        },
                        status=200,
                    )
                else:
                    return JsonResponse(
                        {
                            "success": False,
                            "status": "error",
                            "message": task_result.get("message", ""),
                        }
                    )

        except Exception as e:
            if request.headers.get("HX-Request"):
                return render(
                    request,
                    "job_seekers/partials/error.html",
                    {"message": f"Error checking task status: {str(e)}"},
                    status=500,
                )
            else:
                return JsonResponse(
                    {
                        "success": False,
                        "status": "error",
                        "message": f"Error checking task status: {str(e)}",
                    },
                    status=500,
                )
