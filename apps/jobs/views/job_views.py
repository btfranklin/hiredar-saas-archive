"""
Job-related views for the jobs app.

This module contains views for creating, listing, viewing, editing, and deleting job openings,
providing the core functionality for job management in the application.
"""

from typing import Any, ClassVar, cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import QuerySet
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBase,
    HttpResponseRedirect,
)
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.authentication.types import AuthenticatedUser
from apps.job_seekers.models import JobSeekerProfile
from apps.jobs.models import CandidateMatch
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
    template_name = "jobs/job_opening_create.html"
    fields = [
        "title",
        "description",
        "location",
        "company",
        "salary_min",
        "salary_max",
        "required_skills",
        "experience_years",
        "is_active",
    ]
    success_url = reverse_lazy("jobs:list")

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

        Creates a new job opening, sets the company and recruiter, and runs
        the matching algorithm to find potential candidates.

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

        # Run the matching algorithm (simplified for MVP)
        self._match_candidates(job)

        return HttpResponseRedirect(self.get_success_url())

    def _match_candidates(self, job: JobOpening) -> None:
        """
        Simple matching algorithm for finding potential candidates for a job.

        In a real app, this would use AI for sophisticated matching. For the MVP,
        it uses a basic matching algorithm based on skills and experience.

        Args:
            job: The job opening to match candidates for.
        """
        # Get all job seekers
        job_seekers = JobSeekerProfile.objects.all()

        # For each job seeker, calculate a match score
        for job_seeker in job_seekers:
            # In a real app, this would use NLP to compare skills, experience, etc.
            # For the MVP, we'll use a very simplistic approach

            match_score = 0
            job_seeker_skills = (
                job_seeker.skills_list if hasattr(job_seeker, "skills_list") else []
            )
            required_skills = (
                job.required_skills.split(",") if job.required_skills else []
            )

            # Calculate score based on matching skills
            for skill in required_skills:
                if any(
                    skill.lower() in js_skill.lower() for js_skill in job_seeker_skills
                ):
                    match_score += 20  # Each matching skill adds 20 points

            # Add points for experience match
            seeker_experience = job_seeker.years_of_experience or 0
            if seeker_experience >= job.experience_years:
                match_score += 20

            # Cap the score at 100
            match_score = min(match_score, 100)

            # Create match if score is above threshold
            if match_score >= 40:
                match_type = "top" if match_score >= 70 else "wildcard"
                CandidateMatch.objects.create(
                    job_opening=job,
                    job_seeker=job_seeker,
                    match_score=match_score,
                    match_type=match_type,
                    match_explanation=f"Matched {len([s for s in required_skills if any(s.lower() in js.lower() for js in job_seeker_skills)])} skills and experience requirements",
                )


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
    template_name = "jobs/job_opening_list.html"
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
    template_name = "jobs/job_opening_detail.html"
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
    template_name = "jobs/job_opening_edit.html"
    fields = [
        "title",
        "description",
        "location",
        "company",
        "salary_min",
        "salary_max",
        "required_skills",
        "experience_years",
        "is_active",
    ]
    object: JobOpening | None = None

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """
        Handle GET requests: retrieve the job to edit and render the form.

        This override ensures that self.object is properly set before the template is rendered.
        """
        self.object = cast(JobOpening, self.get_object())
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Get additional context data for the template.

        This ensures that job_opening is properly set in the context.
        """
        context = super().get_context_data(**kwargs)
        # Ensure the job_opening object is properly set in the context
        if "job_opening" not in context:
            context["job_opening"] = self.object
        return context

    def get_success_url(self) -> str:
        """
        Get the URL to redirect to after successful update.

        Returns:
            str: The URL to redirect to.
        """
        job = cast(JobOpening, self.object)
        return reverse("jobs:detail", kwargs={"pk": job.pk})

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """
        Check if the user is the owner of the job before processing the request.

        Args:
            request: The HTTP request.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: The response to the request.
        """
        job = cast(JobOpening, self.get_object())
        # Only allow the owner to edit
        if job.recruiter.user != request.user:
            return redirect("jobs:detail", pk=job.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form: Any) -> HttpResponseRedirect:
        """
        Process the form if it is valid.

        Updates the job opening and handles updating requirements.

        Args:
            form: The validated form.

        Returns:
            HttpResponseRedirect: Redirect to success_url.
        """
        job = form.save()
        # Set the object safely with proper casting
        self.object = cast(JobOpening, job)

        return HttpResponseRedirect(self.get_success_url())


class JobOpeningDeleteView(LoginRequiredMixin, DeleteView):
    """
    View for deleting a job opening.

    This view allows recruiters to delete their job openings.

    Attributes:
        model: The model to delete (JobOpening).
        template_name: The template to render for job deletion confirmation.
        success_url: URL to redirect to after successful deletion.
    """

    model: ClassVar[type[JobOpening]] = JobOpening
    template_name = "jobs/job_opening_confirm_delete.html"
    context_object_name = "job_opening"
    success_url = reverse_lazy("jobs:list")
    object: JobOpening | None = None

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """
        Check if the user is the owner of the job before processing the request.

        Args:
            request: The HTTP request.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: The response to the request.
        """
        job = cast(JobOpening, self.get_object())
        # Only allow the owner to delete
        if job.recruiter.user != request.user:
            return redirect("jobs:detail", pk=job.pk)
        return super().dispatch(request, *args, **kwargs)
