"""
Job opening views for the recruiters app.

This module contains views for creating, listing, viewing, editing, and deleting job openings,
providing the core functionality for job opening management in the application.
"""

import uuid
from typing import Any, ClassVar, cast

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import QuerySet
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBase,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
    View,
)
from django_q.tasks import async_task

from apps.authentication.types import AuthenticatedUser
from apps.matching.models import CandidateMatch
from apps.recruiters.models import (
    JobOpening,
    JobOpeningProcessingTask,
    RecruiterProfile,
)


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
            "apps.recruiters.tasks.process_job_description",
            task_id,
            job_title,
            job_description,
            recruiter_profile.pk,
            hook="apps.recruiters.tasks.job_processing_done",
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


class JobOpeningCreateView(LoginRequiredMixin, CreateView):
    """
    View for creating a new job opening.

    This view allows recruiters to create new job openings, including setting the job
    details, requirements, and skills. It also runs a matching algorithm to find
    potential candidates for the job.

    Attributes:
        model: The model to create (JobOpening).
        template_name: The template to render for job creation.
        fields: Fields to include in the form.
        success_url: URL to redirect to after successful creation.
    """

    model = JobOpening
    template_name = "recruiters/job_openings/create.html"
    fields = [
        # Basic Information
        "title",
        "description",
        "location",
        "company",
        # Job Classification
        "job_level",
        "employment_type",
        # Compensation & Benefits
        "salary_min",
        "salary_max",
        "benefits",
        "additional_perks",
        # Qualifications & Skills
        "required_skills",
        "required_qualifications",
        "soft_skills",
        # Job Details
        "responsibilities",
        "daily_tasks",
        "performance_expectations",
        # Working Conditions
        "working_hours",
        "work_environment",
        "reporting_to",
        "travel_requirements",
        # Status
        "is_active",
    ]
    success_url = reverse_lazy("recruiters:job_openings_list")

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """Ensure only recruiters can access this view."""
        user = cast(AuthenticatedUser, request.user)
        if not user.is_authenticated or user.user_type != "recruiter":
            return redirect("core:home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form: Any) -> HttpResponseRedirect:
        """
        Process the form if it is valid.

        Creates a new job opening, sets the company and recruiter.

        Args:
            form: The validated form.

        Returns:
            HttpResponseRedirect: Redirect to success_url.
        """
        # Set the company and recruiter
        job = form.save(commit=False)
        user = cast(AuthenticatedUser, self.request.user)
        # Set recruiter directly
        job.recruiter = user.recruiter_profile
        job.is_active = True  # Set as active by default
        job.save()

        return HttpResponseRedirect(self.get_success_url())


class JobOpeningListView(LoginRequiredMixin, ListView):
    """
    View for listing job openings.

    This view displays job openings based on user type: recruiters see their own
    job openings, while job seekers see all active jobs.

    Attributes:
        model: The model to list (JobOpening).
        template_name: The template to render for job listing.
        context_object_name: The name of the context variable for the job list.
    """

    model = JobOpening
    template_name = "recruiters/job_openings/list.html"
    context_object_name = "job_openings"

    def get_queryset(self) -> QuerySet[JobOpening]:
        """
        Get the job openings to display based on user type.

        Returns:
            QuerySet[JobOpening]: A queryset of job openings filtered by user type.
        """
        user = cast(AuthenticatedUser, self.request.user)

        if user.user_type == "recruiter":
            # Recruiters see their own job openings
            return JobOpening.objects.filter(recruiter=user.recruiter_profile).order_by(
                "-created_at"
            )
        # Job seekers see all active jobs
        return JobOpening.objects.filter(is_active=True).order_by("-created_at")


class JobOpeningDetailView(LoginRequiredMixin, DetailView):
    """
    View for displaying details of a job opening.

    This view shows all details of a job opening, including description, requirements,
    and application options.
    """

    model: ClassVar[type[JobOpening]] = JobOpening
    template_name = "recruiters/job_openings/detail.html"
    context_object_name = "job_opening"
    object: JobOpening | None = None

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Get context data for rendering the template.

        For recruiters who own the job, adds candidate matches to the context.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            Dict[str, Any]: The context data for the template.
        """
        context = super().get_context_data(**kwargs)
        user = cast(AuthenticatedUser, self.request.user)
        job_opening = cast(JobOpening, self.get_object())

        if user.user_type == "recruiter":
            # Only show candidate matches to the job owner
            if job_opening.recruiter.user == self.request.user:
                # Get candidate matches - use related_name from model definition
                matches = CandidateMatch.objects.filter(job_opening=job_opening)

                context["top_matches"] = matches.filter(match_type="top").order_by(
                    "-match_score"
                )

                context["wildcard_matches"] = matches.filter(
                    match_type="wildcard"
                ).order_by("-match_score")

        return context


class JobOpeningEditView(LoginRequiredMixin, UpdateView):
    """
    View for editing a job opening.

    This view allows recruiters to edit their own job openings, including updating
    job details, requirements, skills, and status.

    Attributes:
        model: The model to update (JobOpening).
        template_name: The template to render for job editing.
        fields: Fields to include in the form.
    """

    model: ClassVar[type[JobOpening]] = JobOpening
    template_name = "recruiters/job_openings/edit.html"
    fields = [
        # Basic Information
        "title",
        "description",
        "location",
        "company",
        # Job Classification
        "job_level",
        "employment_type",
        # Compensation & Benefits
        "salary_min",
        "salary_max",
        "benefits",
        "additional_perks",
        # Qualifications & Skills
        "required_skills",
        "required_qualifications",
        "soft_skills",
        # Job Details
        "responsibilities",
        "daily_tasks",
        "performance_expectations",
        # Working Conditions
        "working_hours",
        "work_environment",
        "reporting_to",
        "travel_requirements",
        # Status
        "is_active",
    ]

    def get_success_url(self) -> str:
        """
        Get the URL to redirect to after a successful edit.

        Returns:
            str: The URL to redirect to.
        """
        return reverse("recruiters:job_openings_detail", kwargs={"pk": self.object.pk})

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """
        Ensure only the recruiter who created the job can edit it.

        Args:
            request: The HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponseBase: The HTTP response.
        """
        user = cast(AuthenticatedUser, request.user)
        job_opening = self.get_object()

        if not user.is_authenticated or user.user_type != "recruiter":
            return redirect("core:home")

        # Check if this recruiter owns the job opening
        if job_opening.recruiter.user != request.user:
            return redirect("core:home")

        return super().dispatch(request, *args, **kwargs)


class JobOpeningDeleteView(LoginRequiredMixin, DeleteView):
    """
    View for deleting a job opening.

    This view allows recruiters to delete their own job openings, with a confirmation
    step to prevent accidental deletion.

    Attributes:
        model: The model to delete (JobOpening).
        template_name: The template to render for confirmation.
        success_url: URL to redirect to after successful deletion.
    """

    model: ClassVar[type[JobOpening]] = JobOpening
    template_name = "recruiters/job_openings/confirm_delete.html"
    success_url = reverse_lazy("recruiters:job_openings_list")

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """
        Ensure only the recruiter who created the job can delete it.

        Args:
            request: The HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponseBase: The HTTP response.
        """
        user = cast(AuthenticatedUser, request.user)
        job_opening = self.get_object()

        if not user.is_authenticated or user.user_type != "recruiter":
            return redirect("core:home")

        # Check if this recruiter owns the job opening
        if job_opening.recruiter.user != request.user:
            return redirect("core:home")

        return super().dispatch(request, *args, **kwargs)
