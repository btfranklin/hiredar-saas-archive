"""Resume processing views for job seekers."""

import logging
import time
import uuid
from typing import Any, cast

from celery import chain
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseBase, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import TemplateView, View

from apps.authentication.models import User
from apps.authentication.types import AuthenticatedUser
from apps.core.tasks import safe_async_task
from apps.core.upload_validators import DEFAULT_RESUME_VALIDATORS
from apps.job_seekers.models import JobSeekerProfile, TalentSheet
from apps.job_seekers.services.talent_pool_manager import TalentPoolManager
from apps.job_seekers.tasks.post_resume_processing_tasks import (
    resume_processing_completed,
)
from apps.job_seekers.views.mixins import HTMXViewMixin, ProfileAccessMixin
from apps.resume_processing.services.resume_processor import ResumeProcessor
from apps.resume_processing.tasks.resume_processing_tasks import (
    handle_resume_upload_task,
    save_resume_file,
)

# Configure logging
logger = logging.getLogger(__name__)

# Alias safe_async_task to async_task
async_task = safe_async_task


class ProfileCreateView(
    LoginRequiredMixin, ProfileAccessMixin, HTMXViewMixin, TemplateView
):
    """Profile creation view for job seekers."""

    template_name = "job_seekers/profile_create.html"

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """Ensure only job seekers can access this view."""
        error_response = self.ensure_job_seeker(request)
        if error_response:
            return error_response
        return super().dispatch(request, *args, **kwargs)

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """Handle GET requests, with special handling for HTMX requests."""
        if self.is_htmx_request(request):
            # For HTMX requests, render just the form partial
            return self.render_for_htmx(
                request, "job_seekers/partials/upload_form.html"
            )

        # For regular requests, render the full page
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add extra context data."""
        context = super().get_context_data(**kwargs)
        # Hide the user menu in the navbar for this page
        context["hide_user_menu"] = True
        return context


class ResumeUploadView(LoginRequiredMixin, ProfileAccessMixin, HTMXViewMixin, View):
    """
    View for handling resume uploads from job seekers.

    This view accepts resume file uploads, saves them to the media directory,
    and queues an asynchronous task to process the resume and update the profile.
    """

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """Handle POST requests for resume uploads."""
        user = cast(AuthenticatedUser, request.user)
        user_model = cast(User, user)

        # Ensure user is a job seeker
        error_response = self.ensure_job_seeker(request)
        if error_response:
            return error_response

        is_htmx = self.is_htmx_request(request)
        logger.info("Resume upload request received - HTMX: %s", is_htmx)

        # Get the uploaded file
        resume_file = request.FILES.get("resume")
        if not resume_file:
            return self.render_htmx_or_json(
                request,
                "job_seekers/partials/error.html",
                {"success": False, "message": "No resume file provided."},
                status=400,
            )

        # Validate uploaded file using shared PDF validators
        filename = getattr(resume_file, "name", "")
        try:
            for validator in DEFAULT_RESUME_VALIDATORS:
                validator(resume_file)
        except ValidationError as ve:
            # Return user-friendly error if validation fails
            return self.render_htmx_or_json(
                request,
                "job_seekers/partials/error.html",
                {"success": False, "message": ve.messages[0]},
                status=400,
            )

        try:
            logger.info("Processing upload for file: %s", filename)

            # Generate a unique filename
            unique_filename = f"{uuid.uuid4()}_{filename}"

            # Save the file
            file_path = save_resume_file(resume_file, unique_filename)

            # Ensure the user has a JobSeekerProfile (create one if it doesn't exist)
            job_seeker_profile = JobSeekerProfile.objects.filter(
                user_owner=user_model
            ).first()
            if job_seeker_profile is None:
                job_seeker_profile = JobSeekerProfile.objects.create(
                    user_owner=user_model
                )

            # Immediately withdraw from talent pool and remove outdated talent sheet
            TalentPoolManager.toggle_talent_pool(user_model, join=False)
            TalentSheet.objects.filter(job_seeker=job_seeker_profile).delete()

            # Expose convenience attribute for the rest of the request lifecycle
            setattr(user_model, "job_seeker_profile", job_seeker_profile)

            profile_id = job_seeker_profile.pk

            # Generate a semantic task ID based on profile and timestamp
            timestamp = int(time.time())
            task_id = f"resume_processing_{profile_id}_{timestamp}"
            logger.info("Created task ID: %s", task_id)

            # Create a tracking record for this task using our service
            task_progress = ResumeProcessor.create_processing_task(user_model, task_id)

            # Create Celery chain for resume processing and completion
            task_chain = chain(
                handle_resume_upload_task.si(  # type: ignore[misc]
                    file_path,
                    profile_id,
                    task_id=task_progress.task_id,
                ),
                resume_processing_completed.s(),  # type: ignore[misc]
            )

            # Execute the chain with semantic naming
            async_result = task_chain.apply_async()  # noqa: F841

            # Update the task to mark the first step as complete
            ResumeProcessor.update_task_progress(
                task_id,
                "file_path_resolved",
                "Resume file saved and ready for processing",
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
            return self.render_htmx_or_json(
                request,
                "job_seekers/partials/error.html",
                {"success": False, "message": f"Error uploading resume: {str(e)}"},
                status=500,
            )


class ResumeProcessingTaskProgressView(
    LoginRequiredMixin, ProfileAccessMixin, HTMXViewMixin, View
):
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
        user_model = cast(User, user)

        # Ensure user is a job seeker
        error_response = self.ensure_job_seeker(request)
        if error_response:
            return error_response

        is_htmx = self.is_htmx_request(request)

        try:
            # Use the service to get the task status, passing the user to match original behavior
            task_progress = ResumeProcessor.get_task_status(task_id, user=user_model)

            if not task_progress:
                return self.render_htmx_or_json(
                    request,
                    "job_seekers/partials/error.html",
                    {"success": False, "message": "Task not found."},
                    status=404,
                )

            # Check if task completed or failed
            if task_progress.status == "completed":
                if is_htmx:
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
                if is_htmx:
                    return self.render_for_htmx(
                        request,
                        "job_seekers/partials/error.html",
                        {"message": task_progress.message or "Task processing failed"},
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

            # Get the progress data
            progress_data = task_progress.to_dict()

            if is_htmx:
                # For HTMX requests, return processing template
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
                return render(request, "job_seekers/partials/processing.html", context)
            else:
                # For non-HTMX requests, return JSON
                return JsonResponse(
                    {
                        "success": True,
                        "status": task_progress.status,
                        "message": task_progress.message,
                        "progress": progress_data,
                    }
                )

        except Exception as e:
            logger.exception("Error checking task status: %s", str(e))
            return self.render_htmx_or_json(
                request,
                "job_seekers/partials/error.html",
                {"success": False, "message": f"Error checking task status: {str(e)}"},
                status=500,
            )
