"""
Candidate-related views for the matching app.

This module contains views for viewing and managing candidate matches for job openings,
including listing candidates, viewing candidate details, and managing shortlists.
"""

from typing import Any, cast

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, HttpResponseBase, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from apps.authentication.types import AuthenticatedUser
from apps.matching.models import CandidateMatch
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

    template_name = "matching/candidate_match_list.html"
    context_object_name = "candidate_matches"
    section = None
    job_opening = None

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """
        Ensure that only the job opening's recruiter can access this view.

        Args:
            request: The HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            HttpResponseBase: The dispatch response.
        """
        self.job_opening = get_object_or_404(JobOpening, pk=self.kwargs["job_id"])
        user = cast(AuthenticatedUser, request.user)

        # Make sure only the recruiter who created the job opening can view matches
        if (
            user.user_type != "recruiter"
            or self.job_opening.recruiter.user.email != user.email
        ):
            return redirect("recruiters:dashboard")

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """
        Get the list of candidate matches for a job opening.

        Returns:
            QuerySet: The candidate matches queryset.
        """
        self.section = self.request.GET.get("section", "top")

        # Start with the base filter for job_opening
        queryset = CandidateMatch.objects.filter(job_opening=self.job_opening)

        # Add match_type filter based on section
        if self.section == "wildcard":
            queryset = queryset.filter(match_type="wildcard")
        else:
            queryset = queryset.filter(match_type="top")

        # Order by match score descending
        return queryset.order_by("-match_score")

    def get_context_data(self, **kwargs):
        """
        Add additional context data.

        Args:
            **kwargs: Arbitrary keyword arguments.

        Returns:
            dict: The context data.
        """
        context = super().get_context_data(**kwargs)
        context["job_opening"] = self.job_opening
        context["section"] = self.section
        context["top_count"] = CandidateMatch.objects.filter(
            job_opening=self.job_opening, match_type="top"
        ).count()
        context["wildcard_count"] = CandidateMatch.objects.filter(
            job_opening=self.job_opening, match_type="wildcard"
        ).count()
        return context


@method_decorator(login_required, name="dispatch")
class CandidateDetailView(LoginRequiredMixin, DetailView):
    """
    View for detailed information about a candidate match.

    This view displays detailed information about a specific candidate match,
    including the job seeker's profile information and the match score.
    Only accessible to the recruiter who owns the job opening.

    Attributes:
        template_name: The template to render for candidate detail.
        context_object_name: The name of the context variable for the match.
    """

    template_name = "matching/candidate_detail.html"
    context_object_name = "match"
    job_opening = None

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """
        Ensure that only the job opening's recruiter can access this view.

        Args:
            request: The HTTP request.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            HttpResponseBase: The dispatch response.
        """
        self.job_opening = get_object_or_404(JobOpening, pk=self.kwargs["job_id"])
        user = cast(AuthenticatedUser, request.user)

        # Make sure only the recruiter who created the job opening can view matches
        if (
            user.user_type != "recruiter"
            or self.job_opening.recruiter.user.email != user.email
        ):
            return redirect("recruiters:dashboard")

        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        """
        Get the candidate match object.

        Args:
            queryset: Optional queryset to use.

        Returns:
            CandidateMatch: The candidate match object.
        """
        return get_object_or_404(
            CandidateMatch,
            job_opening=self.job_opening,
            job_seeker__id=self.kwargs["candidate_id"],
        )

    def get_context_data(self, **kwargs):
        """
        Add additional context data.

        Args:
            **kwargs: Arbitrary keyword arguments.

        Returns:
            dict: The context data.
        """
        context = super().get_context_data(**kwargs)
        context["job_opening"] = self.job_opening
        return context


@login_required
@require_POST
def toggle_shortlist(
    request: HttpRequest, job_id: int, candidate_id: int
) -> HttpResponse:
    """
    Toggle whether a candidate is shortlisted.

    Args:
        request: The HTTP request.
        job_id: The job opening ID.
        candidate_id: The candidate ID.

    Returns:
        HttpResponse: The HTTP response.
    """
    job_opening = get_object_or_404(JobOpening, pk=job_id)
    user = cast(AuthenticatedUser, request.user)

    # Make sure only the recruiter who created the job opening can modify matches
    if user.user_type != "recruiter" or job_opening.recruiter.user.email != user.email:
        return JsonResponse({"status": "error", "message": "Unauthorized"}, status=403)

    match = get_object_or_404(
        CandidateMatch, job_opening=job_opening, job_seeker__id=candidate_id
    )
    match.is_shortlisted = not match.is_shortlisted
    match.save()

    return JsonResponse(
        {
            "status": "success",
            "is_shortlisted": match.is_shortlisted,
        }
    )
