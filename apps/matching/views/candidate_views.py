"""
Candidate-related views for the matching app.

This module contains views for viewing and managing candidate matches for job openings,
including viewing candidate details and managing candidate interactions.
"""

from typing import Any, cast

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, HttpResponseBase, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import DetailView

from apps.authentication.types import AuthenticatedUser
from apps.core.tasks import safe_async_task
from apps.job_seekers.models import JobSeekerProfile as JobSeeker
from apps.matching.models import CandidateMatch, ShortlistedMatch
from apps.matching.tasks.analyze_candidate_match import analyze_candidate_match
from apps.messaging.models import Conversation
from apps.recruiters.models import JobOpening


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
            talent_sheet__job_seeker__id=self.kwargs["candidate_id"],
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

        # Check if this candidate is already shortlisted for this job opening
        context["is_shortlisted"] = ShortlistedMatch.objects.filter(
            job_opening=self.job_opening, candidate_match=self.object
        ).exists()

        # Get existing conversation between the recruiter and job seeker for this job opening
        try:
            # Use filter with multiple conditions instead of repeating parameters
            conversation = (
                Conversation.objects.filter(
                    job_opening=self.job_opening, participants=self.request.user
                )
                .filter(participants=self.object.talent_sheet.job_seeker.user_owner)
                .get()
            )
            context["candidate_conversation"] = conversation
        except Conversation.DoesNotExist:
            context["candidate_conversation"] = None

        return context


def withdraw_interest(request, job_id, candidate_id):
    """
    API endpoint to withdraw interest in a candidate
    """
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Method not allowed"}, status=405
        )

    # Get the job opening and ensure the user has access to it
    job_opening = get_object_or_404(JobOpening, id=job_id)

    # Check if the current user has access to this job opening
    user = cast(AuthenticatedUser, request.user)
    if job_opening.recruiter.user.pk != user.pk:
        return JsonResponse(
            {"status": "error", "message": "Permission denied"}, status=403
        )

    # Get the job seeker
    job_seeker = get_object_or_404(JobSeeker, id=candidate_id)

    # Find and delete the conversation
    try:
        # Use filter with multiple conditions instead of repeating parameters
        conversation = (
            Conversation.objects.filter(job_opening=job_opening, participants=user)
            .filter(
                participants=job_seeker.user_owner,
                status="interest_requested",  # Only delete if status is interest_requested
            )
            .get()
        )
        conversation.delete()

        # Check if this is an HTMX request
        is_htmx = "HX-Request" in request.headers

        if is_htmx:
            # Return the updated button HTML for HTMX
            contact_button_html = """
            <button class="btn btn-primary" onclick="document.getElementById('confirm-interest-modal').showModal()">
                <i class="fas fa-envelope mr-2"></i> Contact Candidate
            </button>
            """
            # Close the modal via HX-Trigger
            response = HttpResponse(contact_button_html)
            response["HX-Trigger"] = '{"closeModal": {"id": "confirm-withdraw-modal"}}'
            response["HX-Reswap"] = "outerHTML"
            response["HX-Target"] = ".flex.gap-2"
            return response
        else:
            # For non-HTMX requests, return JSON
            return JsonResponse({"status": "success"})

    except Conversation.DoesNotExist:
        if "HX-Request" in request.headers:
            return HttpResponse(
                '<div class="alert alert-error">No active interest request found</div>',
                status=404,
            )
        else:
            return JsonResponse(
                {"status": "error", "message": "No active interest request found"},
                status=404,
            )


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
        talent_sheet__job_seeker__id=candidate_id,
    )

    # Toggle shortlist entry
    existing = ShortlistedMatch.objects.filter(
        job_opening=job_opening, candidate_match=candidate_match
    ).first()

    if existing:
        existing.delete()
        is_shortlisted = False
    else:
        ShortlistedMatch.objects.create(
            job_opening=job_opening, candidate_match=candidate_match
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
                '<button type="submit" class="btn btn-success btn-sm">'
                '<i class="fas fa-check mr-1"></i> In Shortlist'
                "</button></form>"
            )
        else:
            button_html = (
                f'<form hx-post="{toggle_url}" hx-target="this" hx-swap="outerHTML">'
                f"{csrf_input}"
                '<button type="submit" class="btn btn-outline btn-sm">'
                '<i class="fas fa-plus mr-1"></i> Add to Shortlist'
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
        talent_sheet__job_seeker__id=candidate_id,
    )

    # If not analyzed yet, trigger analysis and return loading state
    if not candidate_match.is_analyzed:
        # Trigger analysis task if not already running
        # We use a predictable task name to avoid duplicate tasks
        task_name = f"analyze_match_{candidate_match.pk}"

        # Trigger the analysis task
        safe_async_task(
            analyze_candidate_match,
            candidate_match.pk,
            task_name=task_name,
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
