"""Profile views for job seekers."""

from typing import Any, cast

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import redirect
from django.views.generic import DetailView, TemplateView

from apps.authentication.types import AuthenticatedUser
from apps.job_seekers.models import JobSeekerProfile
from apps.messaging.models import Conversation


class ProfileView(LoginRequiredMixin, TemplateView):
    """Profile view for job seekers."""

    template_name = "job_seekers/profile.html"

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """Ensure only job seekers can access this view."""
        user = cast(AuthenticatedUser, request.user)
        if user.user_type != "job_seeker":
            return redirect("core:home")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Get context data for the profile view."""
        context = super().get_context_data(**kwargs)
        user = cast(AuthenticatedUser, self.request.user)

        # Add job_seeker_profile to context
        context["job_seeker_profile"] = user.job_seeker_profile

        return context


class ResumeView(LoginRequiredMixin, DetailView):
    """
    View for recruiters to view a job seeker's full resume.

    Access is only granted if:
    1. The user is a recruiter
    2. There's a conversation between the recruiter and job seeker
    3. The conversation status is 'candidate_interested'
    """

    model = JobSeekerProfile
    template_name = "job_seekers/resume_view.html"
    context_object_name = "profile"

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """
        Check permissions before allowing access to the resume.

        Ensures that:
        1. The user is a recruiter
        2. There's a conversation with the job seeker
        3. The job seeker has expressed interest
        """
        user = cast(AuthenticatedUser, request.user)

        # Only recruiters can view resumes
        if user.user_type != "recruiter":
            messages.error(request, "Only recruiters can view candidate resumes.")
            return redirect("core:home")

        # Get the job seeker profile
        profile = self.get_object()
        job_seeker = profile.user_owner

        # Check if there's a conversation where the job seeker has expressed interest
        conversation = Conversation.objects.filter(
            Q(participants=user)
            & Q(participants=job_seeker)
            & Q(status="candidate_interested")
        ).first()

        if not conversation:
            messages.error(
                request,
                "You can only view resumes of candidates who have expressed interest in your job openings.",
            )
            return redirect("recruiters:dashboard")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add conversation to context."""
        context = super().get_context_data(**kwargs)
        profile = self.get_object()

        # Get the conversation for context
        conversation = Conversation.objects.filter(
            Q(participants=self.request.user)
            & Q(participants=profile.user_owner)
            & Q(status="candidate_interested")
        ).first()

        context["conversation"] = conversation
        context["job_opening"] = conversation.job_opening if conversation else None

        return context


class SettingsView(LoginRequiredMixin, TemplateView):
    """Settings view for job seekers."""

    template_name = "job_seekers/settings.html"

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """Ensure only job seekers can access this view."""
        user = cast(AuthenticatedUser, request.user)
        if user.user_type != "job_seeker":
            return redirect("core:home")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Get context data for the settings view."""
        context = super().get_context_data(**kwargs)
        return context
