"""
Candidate-related views for the matching app.

This module contains views for viewing and managing candidate matches for job openings,
including viewing candidate details and managing candidate interactions.
"""

import logging
from typing import Any, cast

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F
from django.http import HttpRequest, HttpResponse, HttpResponseBase, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import DetailView

from apps.authentication.types import AuthenticatedUser
from apps.core.tasks import safe_async_task
from apps.matching.models import CandidateMatch, ShortlistedMatch
from apps.matching.tasks.analyze_candidate_match import analyze_candidate_match
from apps.recruiters.models import JobOpening, RecruiterProfile

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")  # type: ignore
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
            candidate_profile__id=self.kwargs["candidate_id"],
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
        context["candidate_profile"] = self.object.candidate_profile
        context["tab"] = self.request.GET.get("tab", "profile")

        # Check if this candidate is already shortlisted for this job opening
        context["is_shortlisted"] = ShortlistedMatch.objects.filter(
            job_opening=self.job_opening, candidate_match=self.object
        ).exists()

        context["candidate_conversation"] = None
        context["show_shortlist"] = True

        return context


def add_to_shortlist(request: HttpRequest, job_id: int, candidate_id: int):
    """Add a candidate match to the recruiter's shortlist for this job opening."""

    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Method not allowed"}, status=405
        )

    # Ensure the job opening exists and belongs to the current recruiter
    job_opening = get_object_or_404(JobOpening, id=job_id)
    user = cast(AuthenticatedUser, request.user)
    if job_opening.recruiter.user.pk != user.pk:
        return JsonResponse(
            {"status": "error", "message": "Permission denied"}, status=403
        )

    # Get the candidate match
    candidate_match = get_object_or_404(
        CandidateMatch,
        job_opening=job_opening,
        candidate_profile__id=candidate_id,
    )

    # Toggle shortlist entry
    existing = ShortlistedMatch.objects.filter(
        job_opening=job_opening, candidate_match=candidate_match
    ).first()

    if existing:
        existing.delete()
        RecruiterProfile.objects.filter(pk=job_opening.recruiter.pk).update(
            total_candidates_shortlisted=F("total_candidates_shortlisted") - 1
        )
        is_shortlisted = False
    else:
        ShortlistedMatch.objects.create(
            job_opening=job_opening, candidate_match=candidate_match
        )
        RecruiterProfile.objects.filter(pk=job_opening.recruiter.pk).update(
            total_candidates_shortlisted=F("total_candidates_shortlisted") + 1
        )
        is_shortlisted = True

    if request.headers.get("HX-Request") == "true":
        # Build CSRF input and target URL
        csrf_token_value = request.META.get("CSRF_COOKIE", "")
        csrf_input = f'<input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token_value}">'  # noqa: E501
        toggle_url = reverse(
            "matching:add_to_shortlist", args=[job_opening.pk, candidate_id]
        )

        if is_shortlisted:
            button_html = (
                f'<form hx-post="{toggle_url}" hx-target="this" hx-swap="outerHTML">'
                f"{csrf_input}"
                '<button type="submit" class="btn btn-success">'
                '<i class="fas fa-check mr-2"></i> In Shortlist'
                "</button></form>"
            )
        else:
            button_html = (
                f'<form hx-post="{toggle_url}" hx-target="this" hx-swap="outerHTML">'
                f"{csrf_input}"
                '<button type="submit" class="btn btn-outline">'
                '<i class="fas fa-plus mr-2"></i> Add to Shortlist'
                "</button></form>"
            )

        return HttpResponse(button_html)

    return JsonResponse({"status": "success", "is_shortlisted": is_shortlisted})


def remove_from_shortlist(request: HttpRequest, job_id: int, shortlist_id: int):
    """Remove a shortlisted match via POST."""

    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Method not allowed"}, status=405
        )

    shortlist_obj = get_object_or_404(ShortlistedMatch, id=shortlist_id)

    user = cast(AuthenticatedUser, request.user)
    # Only the recruiter who owns the job can remove
    if shortlist_obj.job_opening.recruiter.user.pk != user.pk:
        return JsonResponse(
            {"status": "error", "message": "Permission denied"}, status=403
        )

    shortlist_obj.delete()
    RecruiterProfile.objects.filter(pk=shortlist_obj.job_opening.recruiter.pk).update(
        total_candidates_shortlisted=F("total_candidates_shortlisted") - 1
    )

    if request.headers.get("HX-Request") == "true":
        # Inform front-end to refresh shortlist tab and counts
        import json

        response = HttpResponse("")  # row deletion already handled via hx-swap
        # Trigger a custom event so the tabs can be reloaded with updated counts
        response["HX-Trigger"] = json.dumps({"shortlistUpdated": {}})
        return response

    return JsonResponse({"status": "success"})


@login_required
def candidate_match_analysis_status(
    request: HttpRequest, job_id: int, candidate_id: int
) -> HttpResponse:
    """
    HTMX endpoint to check the analysis status of a candidate match.

    This view is used for polling to update the UI when analysis is complete.
    """
    # Ensure the job opening exists and belongs to the current recruiter
    job_opening = get_object_or_404(JobOpening, id=job_id)
    user = cast(AuthenticatedUser, request.user)

    if user.user_type != "recruiter" or job_opening.recruiter.user.email != user.email:
        return HttpResponse("Unauthorized", status=403)

    # Get the candidate match
    candidate_match = get_object_or_404(
        CandidateMatch,
        job_opening=job_opening,
        candidate_profile__id=candidate_id,
    )

    # If not analyzed yet, trigger analysis and return loading state
    if not candidate_match.is_analyzed:
        # Trigger analysis task if not already running
        # We use a predictable task name to avoid duplicate tasks
        task_name = f"analyze_match_{candidate_match.pk}"

        # Trigger the analysis task with debug logging
        try:
            task_id = safe_async_task(
                analyze_candidate_match,
                candidate_match.pk,
                task_name=task_name,
            )
            if task_id:
                logger.info(
                    "Enqueued analyze_candidate_match | task_id=%s candidate_match_id=%s queue=default",
                    task_id,
                    candidate_match.pk,
                )
            else:
                logger.info(
                    "No task enqueued (possibly already running) | candidate_match_id=%s",
                    candidate_match.pk,
                )
        except Exception as e:  # pragma: no cover – defensive logging
            logger.error(
                "Failed to enqueue analyze_candidate_match | candidate_match_id=%s error=%s",
                candidate_match.pk,
                str(e),
                exc_info=True,
            )

        return render(
            request,
            "matching/partials/analysis_loading.html",
            {
                "candidate_match": candidate_match,
            },
        )

    # Analysis is complete, return the analysis content
    return render(
        request,
        "matching/partials/analysis_complete.html",
        {
            "candidate_match": candidate_match,
        },
    )
