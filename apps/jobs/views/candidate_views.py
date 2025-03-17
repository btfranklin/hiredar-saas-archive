"""
Candidate-related views for the jobs app.

This module contains views for viewing and managing candidate matches for job openings,
including listing candidates, viewing candidate details, and managing shortlists.
"""

from typing import Any, Optional, Union, cast

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBase,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from apps.authentication.types import AuthenticatedUser
from apps.jobs.models import CandidateMatch
from apps.recruiters.models import JobOpening


@method_decorator(login_required, name="dispatch")
class CandidateMatchListView(LoginRequiredMixin, ListView):
    """
    View for listing candidate matches for a job opening.

    This view displays all candidate matches for a specific job opening,
    categorized as top matches and wildcard matches. Only accessible to
    the recruiter who owns the job opening.

    Attributes:
        template_name: The template to render for candidate match listing.
        context_object_name: The name of the context variable for the matches.
    """

    template_name = "jobs/candidate_match_list.html"
    context_object_name = "candidate_matches"

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """
        Check permissions and set up job opening before processing the request.

        Ensures the user is a recruiter and owns the job opening.

        Args:
            request: The HTTP request.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponseBase: The response to the request.
        """
        # Only allow recruiters
        user = cast(AuthenticatedUser, request.user)
        if user.user_type != "recruiter":
            return redirect("core:home")

        # Get the job opening
        self.job_opening = get_object_or_404(JobOpening, pk=self.kwargs["job_id"])

        # Only allow the owner to see matches
        if self.job_opening.recruiter.user != user:
            return redirect("jobs:list")

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """
        Get the candidate matches to display for the job opening.

        Returns:
            QuerySet: A queryset of candidate matches for the job opening.
        """
        return (
            CandidateMatch.objects.filter(job_opening=self.job_opening)
            .select_related("job_seeker")
            .order_by("-match_score")
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Get context data for rendering the template.

        Adds the job opening and splits matches by type (top and wildcard).

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            dict[str, Any]: The context data for the template.
        """
        context = super().get_context_data(**kwargs)
        context["job_opening"] = self.job_opening

        # Split matches by type
        context["top_matches"] = self.get_queryset().filter(match_type="top")
        context["wildcard_matches"] = self.get_queryset().filter(match_type="wildcard")

        return context


@method_decorator(login_required, name="dispatch")
class CandidateDetailView(LoginRequiredMixin, DetailView):
    """
    View for viewing a candidate's profile in the context of a job match.

    This view displays the details of a candidate match, including the candidate's
    profile and match information. Only accessible to the recruiter who owns the
    job opening.

    Attributes:
        template_name: The template to render for candidate detail view.
        context_object_name: The name of the context variable for the match.
    """

    template_name = "jobs/candidate_detail.html"
    context_object_name = "candidate_match"
    model = CandidateMatch
    object: CandidateMatch | None = None

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """
        Check if the user is a recruiter before processing the request.

        Args:
            request: The HTTP request.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponseBase: The response to the request.
        """
        # Only allow recruiters
        user = cast(AuthenticatedUser, request.user)
        if user.user_type != "recruiter":
            return redirect("core:home")

        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        """
        Get the candidate match object to display.

        Returns:
            CandidateMatch: The candidate match object.
        """
        return get_object_or_404(
            CandidateMatch,
            job_opening_id=self.kwargs["job_id"],
            job_seeker_id=self.kwargs["candidate_id"],
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Get context data for rendering the template.

        Adds the job opening and job seeker to the context.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            dict[str, Any]: The context data for the template.
        """
        context = super().get_context_data(**kwargs)
        candidate_match = self.get_object()
        context["job_opening"] = candidate_match.job_opening
        context["job_seeker"] = candidate_match.job_seeker
        return context


@require_POST
@login_required
def toggle_shortlist(
    request: HttpRequest, job_id: int, candidate_id: int
) -> Union[HttpResponse, JsonResponse, HttpResponseRedirect]:
    """
    Toggle shortlisting status for a candidate.

    This function allows recruiters to add or remove candidates from their shortlist
    for a job opening. It supports both HTMX and regular requests.

    Args:
        request: The HTTP request.
        job_id: The ID of the job opening.
        candidate_id: The ID of the candidate (job seeker profile).

    Returns:
        Union[HttpResponse, JsonResponse, HttpResponseRedirect]:
            The appropriate response based on the request type.
    """
    # Ensure user is a recruiter
    user = cast(AuthenticatedUser, request.user)
    if user.user_type != "recruiter":
        return HttpResponse(status=403)

    # Get the candidate match
    candidate_match = get_object_or_404(
        CandidateMatch, job_opening_id=job_id, job_seeker_id=candidate_id
    )

    # Ensure the recruiter owns the job opening
    if candidate_match.job_opening.recruiter.user != user:
        return HttpResponse(status=403)

    # Toggle the shortlist status
    candidate_match.is_shortlisted = not candidate_match.is_shortlisted
    candidate_match.save()

    # If this is an HTMX request, return the updated button
    if request.headers.get("HX-Request"):
        context = {
            "candidate_match": candidate_match,
            "job_opening": candidate_match.job_opening,
            "job_seeker": candidate_match.job_seeker,
        }
        return JsonResponse(
            {
                "is_shortlisted": candidate_match.is_shortlisted,
                "button_html": f"""
            <button class="{'text-success' if candidate_match.is_shortlisted else ''}"
                    hx-post="{reverse('jobs:toggle_shortlist', args=[job_id, candidate_id])}"
                    hx-swap="outerHTML">
                <i class="fas {'fa-check-circle' if candidate_match.is_shortlisted else 'fa-circle'} mr-2"></i>
                {'Shortlisted' if candidate_match.is_shortlisted else 'Add to Shortlist'}
            </button>
            """,
            }
        )

    # For non-HTMX requests, redirect back to the candidate detail page
    return redirect("jobs:candidate_detail", job_id=job_id, candidate_id=candidate_id)
