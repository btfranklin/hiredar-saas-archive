"""
Job opening views for the recruiters app.

This module contains views for creating, listing, viewing, editing, and deleting job openings,
providing the core functionality for job opening management in the application.
"""

from typing import Any, ClassVar, cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import QuerySet
from django.http import (
    HttpRequest,
    HttpResponseBadRequest,
    HttpResponseBase,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.authentication.types import AuthenticatedUser
from apps.job_seekers.models import CandidatePool
from apps.matching.models import CandidateMatch
from apps.recruiters.models import JobOpening


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
        "status",
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
        # Set status as active by default if not set
        if not job.status:
            job.status = "active"
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
        return JobOpening.objects.filter(status="active").order_by("-created_at")


class JobOpeningDetailView(LoginRequiredMixin, DetailView):
    """
    View for displaying details of a job opening.

    This view shows all details of a job opening, including description, requirements,
    and application options.
    """

    model: ClassVar[type[JobOpening]] = JobOpening
    template_name: str = "recruiters/job_openings/detail.html"
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
        job_opening = self.get_object()

        # Get the tab parameter from the URL, default to 'details'
        context["tab"] = self.request.GET.get("tab", "details")
        # Get the view parameter from the URL, default to 'processed'
        context["view"] = self.request.GET.get("view", "processed")
        # Get the section parameter from the URL, default to 'holistic'
        context["section"] = self.request.GET.get("section", "holistic")

        if user.user_type == "recruiter":
            # Only show candidate pools and matches to the job owner
            if job_opening.recruiter.user == self.request.user:
                # Load the recruiter's pools
                context["candidate_pools"] = CandidatePool.objects.filter(
                    recruiter=self.request.user
                )
                # Determine selected pool (from query param or stored value)
                selected_pool_id = int(
                    self.request.GET.get("pool_id", job_opening.candidate_pool_id)
                )
                # Persist any change to the job opening
                if selected_pool_id != job_opening.candidate_pool_id:
                    job_opening.candidate_pool_id = selected_pool_id
                    job_opening.save(update_fields=["candidate_pool_id"])
                context["candidate_pool_id"] = selected_pool_id
                # Filter matches by selected pool
                if selected_pool_id != 0:
                    matches = CandidateMatch.objects.filter(
                        job_opening=job_opening,
                        talent_sheet__job_seeker__candidate_pool_id=selected_pool_id,
                    )
                else:
                    matches = CandidateMatch.objects.none()
                # Determine matches for requested section
                section = context["section"]
                if selected_pool_id != 0:
                    if section == "wildcard":
                        context["candidate_matches"] = matches.filter(
                            match_type="wildcard"
                        ).order_by("-wildcard_score")
                    elif section == "skills":
                        context["candidate_matches"] = matches.filter(
                            match_type="skills"
                        ).order_by("-skills_score")
                    elif section == "experience":
                        context["candidate_matches"] = matches.filter(
                            match_type="experience"
                        ).order_by("-experience_score")
                    elif section == "qualifications":
                        context["candidate_matches"] = matches.filter(
                            match_type="qualifications"
                        ).order_by("-qualifications_score")
                    else:
                        context["candidate_matches"] = matches.filter(
                            match_type="holistic"
                        ).order_by("-holistic_score")
                else:
                    context["candidate_matches"] = []
                # Compute counts (for tabs)
                context["holistic_count"] = matches.filter(
                    match_type="holistic"
                ).count()
                context["skills_count"] = matches.filter(match_type="skills").count()
                context["experience_count"] = matches.filter(
                    match_type="experience"
                ).count()
                context["wildcard_count"] = matches.filter(
                    match_type="wildcard"
                ).count()
                context["qualifications_count"] = matches.filter(
                    match_type="qualifications"
                ).count()

        return context

    def get_template_names(self) -> list[str]:
        """
        Return template names for HTMX pool updates or tab clicks.

        If this is an HTMX request and 'pool_id' is in GET, swap only the tab content.
        Otherwise if HTMX, swap the full tabs-container (tabs + content).
        Otherwise render the full page template.
        """
        if self.request.headers.get("HX-Request") == "true":
            if "pool_id" in self.request.GET:
                return ["recruiters/job_openings/tab_content.html"]
            return ["recruiters/job_openings/partial_tabs_container.html"]
        return [self.template_name]


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
    context_object_name = "job_opening"
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
        "status",
    ]

    def get_success_url(self) -> str:
        """
        Get the URL to redirect to after a successful edit.

        Returns:
            str: The URL to redirect to.
        """
        # Keep the basic fallback for the NoReverseMatch issue
        pk = self.object.pk if self.object and self.object.pk else self.kwargs.get("pk")
        return reverse("recruiters:job_openings_detail", kwargs={"pk": pk})

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

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Get context data for rendering the template.

        Pass choice lists so the template can render select and radio helpers
        Include verbose, user-friendly labels + descriptions for each status option
        """
        context = super().get_context_data(**kwargs)

        # Pass choice lists so the template can render select and radio helpers
        context["JOB_LEVEL_CHOICES"] = JobOpening.JOB_LEVEL_CHOICES
        context["EMPLOYMENT_TYPE_CHOICES"] = JobOpening.EMPLOYMENT_TYPE_CHOICES

        # Include verbose, user-friendly labels + descriptions for each status option
        context["STATUS_CHOICES"] = (
            (
                "draft",
                "Draft",
                "The job is saved but not publicly visible yet.",
            ),
            (
                "active",
                "Active",
                "The job opening is publicly visible and can receive applications.",
            ),
            (
                "closed",
                "Closed",
                "The job opening is no longer accepting applications.",
            ),
        )

        return context


class JobOpeningDeleteView(LoginRequiredMixin, DeleteView):
    """
    View for deleting a job opening.

    This view allows recruiters to delete their own job openings, with a confirmation
    step to prevent accidental deletion.

    Attributes:
        model: The model to delete (JobOpening).
        template_name: The template to render for confirmation.
        context_object_name: The name of the context variable for the job opening.
        success_url: URL to redirect to after successful deletion.
    """

    model: ClassVar[type[JobOpening]] = JobOpening
    template_name = "recruiters/job_openings/confirm_delete.html"
    context_object_name = "job_opening"
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


class JobOpeningStatusChangeView(LoginRequiredMixin, View):
    """View to change the status of a job opening via HTMX."""

    def post(self, request: HttpRequest, pk: int, action: str) -> HttpResponseBase:
        user = cast(AuthenticatedUser, request.user)
        job_opening = get_object_or_404(
            JobOpening, pk=pk, recruiter=user.recruiter_profile
        )
        if action == "activate":
            new_status = "active"
        elif action == "to_draft":
            new_status = "draft"
        elif action == "close":
            new_status = "closed"
        else:
            return HttpResponseBadRequest("Invalid action")
        job_opening.status = new_status
        job_opening.save(update_fields=["status"])
        if request.headers.get("HX-Request") == "true":
            return render(
                request,
                "recruiters/job_openings/state_buttons.html",
                {"job_opening": job_opening},
            )
        return redirect("recruiters:job_openings_detail", pk=pk)
