"""Resume processing views for job seekers."""

import uuid
from typing import Any, cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponseBase, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, View
from django_q.tasks import async_task, result

from apps.authentication.types import AuthenticatedUser
from apps.job_seekers.models import ResumeProcessingTaskProgress
from apps.job_seekers.tasks import handle_resume_upload_task, save_resume_file


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

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        """Handle POST requests for resume uploads."""
        user = cast(AuthenticatedUser, request.user)

        # Ensure user is a job seeker
        if user.user_type != "job_seeker":
            return JsonResponse(
                {"success": False, "message": "Only job seekers can upload resumes."},
                status=403,
            )

        # Get the uploaded file
        resume_file = request.FILES.get("resume")
        if not resume_file:
            return JsonResponse(
                {"success": False, "message": "No resume file provided."},
                status=400,
            )

        # Validate file type (PDF only)
        filename = getattr(resume_file, "name", "")
        if not filename.lower().endswith(".pdf"):
            return JsonResponse(
                {"success": False, "message": "Only PDF files are accepted."},
                status=400,
            )

        try:
            # Generate a unique filename
            unique_filename = f"{uuid.uuid4()}_{filename}"

            # Save the file
            file_path = save_resume_file(resume_file, unique_filename)

            # Get job seeker profile ID
            job_seeker_profile = getattr(user, "job_seeker_profile", None)
            if job_seeker_profile is None:
                return JsonResponse(
                    {"success": False, "message": "Job seeker profile not found."},
                    status=400,
                )

            profile_id = job_seeker_profile.pk

            # Generate a unique ID for the task
            task_id = str(uuid.uuid4())

            # Queue the resume processing task with a completion hook
            async_task(
                handle_resume_upload_task,
                file_path,
                profile_id,
                task_id=task_id,
                task_name=f"resume_processing_{task_id}",
                hook="apps.job_seekers.tasks.hooks.resume_processing_completed",
            )

            # Return success response with task ID and status URL
            status_url = reverse("job_seekers:task_status", kwargs={"task_id": task_id})
            redirect_url = reverse("job_seekers:dashboard")

            return JsonResponse(
                {
                    "success": True,
                    "message": "Resume uploaded successfully. Processing in progress.",
                    "task_id": task_id,
                    "status_url": status_url,
                    "redirect_url": redirect_url,
                }
            )

        except Exception as e:
            return JsonResponse(
                {"success": False, "message": f"Error uploading resume: {str(e)}"},
                status=500,
            )


class ResumeProcessingTaskProgressView(LoginRequiredMixin, View):
    """
    View for checking the status of asynchronous resume processing tasks.

    This view returns the current status of a task by its ID.
    """

    def get(
        self, request: HttpRequest, task_id: str, *args: Any, **kwargs: Any
    ) -> JsonResponse:
        """Get the status of a task by its ID."""
        user = cast(AuthenticatedUser, request.user)

        # Ensure user is a job seeker
        if user.user_type != "job_seeker":
            return JsonResponse(
                {"success": False, "message": "Unauthorized"}, status=403
            )

        try:
            # First check the TaskProgress model for detailed progress information
            try:
                task_progress = ResumeProcessingTaskProgress.objects.get(
                    task_id=task_id, user=user
                )

                # Return detailed progress information
                return JsonResponse(
                    {
                        "success": True,
                        "status": task_progress.status,
                        "message": task_progress.message,
                        "progress": task_progress.to_dict(),
                    }
                )
            except ResumeProcessingTaskProgress.DoesNotExist:
                # Fall back to checking Django Q2 result
                pass

            # Get the task result from Django Q2
            task_result = result(task_id)

            if task_result is None:
                # Task is still running
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
            return JsonResponse(
                {
                    "success": True,
                    "status": task_result.get("status", "error"),
                    "message": task_result.get("message", ""),
                    "profile_data": task_result.get("profile_data", {}),
                }
            )

        except Exception as e:
            return JsonResponse(
                {
                    "success": False,
                    "status": "error",
                    "message": f"Error checking task status: {str(e)}",
                },
                status=500,
            )
