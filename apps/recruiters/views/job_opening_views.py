"""
Job opening views for the recruiters app.

This module contains views for creating, listing, viewing, editing, and deleting job openings,
providing the core functionality for job opening management in the application.
"""

from typing import Any, ClassVar, cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import CharField, QuerySet, Value
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
from apps.candidates.models import CandidatePool
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

    # ------------------------------------------------------------------
    # Access control: Recruiters only
    # ------------------------------------------------------------------
    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """Allow only authenticated recruiter accounts to view this page.

        Any request coming from a non-recruiter (job-seeker, admin impersonation, or
        anonymous) is blocked with HTTP 403 to avoid accidentally exposing
        recruiter-only tooling like candidate tabs or status buttons.
        """
        user = cast(AuthenticatedUser, request.user)

        if not user.is_authenticated or user.user_type != "recruiter":
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

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
                available_pool_ids = set(
                    context["candidate_pools"].values_list("id", flat=True)
                )
                requested_pool = self.request.GET.get("pool_id")
                try:
                    requested_pool_id = int(requested_pool) if requested_pool else None
                except ValueError:
                    requested_pool_id = None

                default_pool_id = (
                    job_opening.candidate_pool_id
                    if job_opening.candidate_pool_id in available_pool_ids
                    or job_opening.candidate_pool_id == 0
                    else 0
                )
                selected_pool_id = (
                    requested_pool_id
                    if requested_pool_id is not None
                    else default_pool_id
                )

                if selected_pool_id not in available_pool_ids and selected_pool_id != 0:
                    selected_pool_id = 0

                # Persist any change to the job opening
                if selected_pool_id != job_opening.candidate_pool_id:
                    job_opening.candidate_pool_id = selected_pool_id
                    job_opening.save(update_fields=["candidate_pool_id"])
                context["candidate_pool_id"] = selected_pool_id
                # ------------------------------------------------------------------
                # Build the base queryset for matches on this job opening.
                # ``candidate_pool_id`` semantics:
                #   • 0  ⇒  Aggregate matches from every pool owned by the recruiter
                #   • n>0 ⇒  Restrict to a specific CandidatePool uploaded by the recruiter
                # ------------------------------------------------------------------
                matches = CandidateMatch.objects.filter(job_opening=job_opening).filter(
                    talent_sheet__job_seeker__candidate_pool__recruiter=user
                )

                if selected_pool_id > 0:
                    # Specific candidate pool – restrict to that pool ID
                    matches = matches.filter(
                        talent_sheet__job_seeker__candidate_pool_id=selected_pool_id
                    )
                # Determine matches for requested section
                section = context["section"]

                if section == "wildcard":
                    candidate_matches_qs = (
                        matches.filter(wildcard_score__gt=0)
                        .annotate(
                            match_type=Value("wildcard", output_field=CharField())
                        )
                        .order_by("-wildcard_score")
                    )
                elif section == "skills":
                    candidate_matches_qs = (
                        matches.filter(skills_score__gt=0)
                        .annotate(match_type=Value("skills", output_field=CharField()))
                        .order_by("-skills_score")
                    )
                elif section == "experience":
                    candidate_matches_qs = (
                        matches.filter(experience_score__gt=0)
                        .annotate(
                            match_type=Value("experience", output_field=CharField())
                        )
                        .order_by("-experience_score")
                    )
                elif section == "qualifications":
                    candidate_matches_qs = (
                        matches.filter(qualifications_score__gt=0)
                        .annotate(
                            match_type=Value("qualifications", output_field=CharField())
                        )
                        .order_by("-qualifications_score")
                    )
                else:
                    candidate_matches_qs = (
                        matches.filter(holistic_score__gt=0)
                        .annotate(
                            match_type=Value("holistic", output_field=CharField())
                        )
                        .order_by("-holistic_score")
                    )

                context["candidate_matches"] = candidate_matches_qs
                context["has_candidate_matches"] = candidate_matches_qs.exists()
                # Compute counts (for tabs)
                context["holistic_count"] = matches.filter(holistic_score__gt=0).count()
                context["skills_count"] = matches.filter(skills_score__gt=0).count()
                context["experience_count"] = matches.filter(
                    experience_score__gt=0
                ).count()
                context["wildcard_count"] = matches.filter(wildcard_score__gt=0).count()
                context["qualifications_count"] = matches.filter(
                    qualifications_score__gt=0
                ).count()
                is_htmx_request = (
                    self.request.headers.get("HX-Request", "").lower() == "true"
                )
                context["should_poll_for_matches"] = (
                    not context["has_candidate_matches"] and not is_htmx_request
                )

                # --- Shortlist -----------------------------------------------------------------
                shortlist_qs = job_opening.shortlisted_matches.select_related(
                    "candidate_match",
                    "candidate_match__talent_sheet",
                    "candidate_match__talent_sheet__job_seeker",
                    "candidate_match__talent_sheet__job_seeker__user_owner",
                ).order_by("-created_at")

                context["shortlist"] = shortlist_qs
                context["shortlist_count"] = shortlist_qs.count()

                # If current tab is shortlist, ensure candidate_pool_id persists for UI reloads

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
