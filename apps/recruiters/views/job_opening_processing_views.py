"""
Job opening processing views for the recruiters app.

This module contains views for processing text job descriptions and
tracking the status of job opening creation tasks.
"""

import uuid

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View
from django_q.tasks import async_task

from apps.recruiters.models import JobOpeningProcessingTask, RecruiterProfile


class TextProcessJobOpeningView(LoginRequiredMixin, UserPassesTestMixin, View):
    """View for processing a text job description and creating a job opening."""

    def test_func(self) -> bool:
        """Verify the user is a recruiter."""
        return self.request.user.user_type == "recruiter"

    def post(self, request: HttpRequest) -> HttpResponse:
        """Process the text job description and queue an async task."""
        job_title = request.POST.get("job_title", "").strip()
        job_description = request.POST.get("job_description", "").strip()

        if not job_title or not job_description:
            messages.error(request, "Please provide both a job title and description.")
            return redirect("recruiters:job_openings_create")

        # Get the recruiter profile
        recruiter_profile = RecruiterProfile.objects.get(user=request.user)

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
            task_id,
            job_title,
            job_description,
            recruiter_profile.pk,
            hook="apps.recruiters.tasks.hooks.job_processing_done",
        )

        # Redirect to the processing status page
        return redirect("recruiters:job_openings_process_status", task_id=task_id)


class JobOpeningTaskStatusView(LoginRequiredMixin, UserPassesTestMixin, View):
    """View for checking the status of a job opening processing task."""

    def test_func(self) -> bool:
        """Verify the user is a recruiter."""
        return self.request.user.user_type == "recruiter"

    def get(self, request: HttpRequest, task_id: str) -> HttpResponse:
        """
        Display the task status page for HTML requests or
        return JSON status for AJAX requests.
        """
        task = get_object_or_404(
            JobOpeningProcessingTask,
            task_id=task_id,
            recruiter__user=request.user,
        )

        # For AJAX requests, return JSON status
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(task.to_dict())

        # For regular requests, render the status template
        return render(
            request,
            "recruiters/job_openings/process_status.html",
            {"task": task},
        )
