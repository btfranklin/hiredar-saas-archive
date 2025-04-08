"""
Candidate-related views for the matching app.

This module contains views for viewing and managing candidate matches for job openings,
including viewing candidate details and managing candidate interactions.
"""

from typing import Any, cast

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.generic import DetailView

from apps.authentication.types import AuthenticatedUser
from apps.matching.models import CandidateMatch
from apps.recruiters.models import JobOpening


@method_decorator(login_required, name="dispatch")
class CandidateDetailView(LoginRequiredMixin, DetailView):
    """
    View for detailed information about a candidate match.

    This view displays detailed information about a specific candidate match,
    including the job seeker's profile information and the match score.
    Only accessible to the recruiter who owns the job opening.

    Attributes:
        template_name: The template to render for candidate match details.
        context_object_name: The name of the context variable for the match.
    """

    template_name = "matching/candidate_match_detail.html"
    context_object_name = "candidate_match"
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
            talent_sheet__job_seeker__id=self.kwargs["candidate_id"],
            match_type="holistic",  # Default to holistic match for detail view
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
        context["talent_sheet"] = self.object.talent_sheet
        context["job_seeker"] = self.object.talent_sheet.job_seeker
        return context
