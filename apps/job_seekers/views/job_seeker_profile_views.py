"""Profile views for job seekers."""

from typing import Any, cast

from allauth.account.models import EmailAddress
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import redirect
from django.views.generic import DetailView, TemplateView

from apps.authentication.types import AuthenticatedUser
from apps.job_seekers.models import JobSeekerProfile
from apps.job_seekers.services import ProfileManager
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

        # Add job_seeker_profile to context using ProfileManager
        context["job_seeker_profile"] = ProfileManager.get_profile_for_user(user)

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

        # Allow recruiters to view resumes from pools they own
        if profile.candidate_pool and profile.candidate_pool.recruiter == user:
            return super().dispatch(request, *args, **kwargs)

        job_seeker = profile.user_owner

        # Check if there's a conversation where the job seeker has expressed interest
        conversation = (
            Conversation.objects.filter(participants=user)
            .filter(participants=job_seeker)
            .first()
        )

        if conversation and conversation.status not in [
            "candidate_interested",
            "active",
        ]:
            conversation = None

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
        conversation = (
            Conversation.objects.filter(participants=self.request.user)
            .filter(participants=profile.user_owner)
            .first()
        )

        if conversation and conversation.status not in [
            "candidate_interested",
            "active",
        ]:
            conversation = None

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

        # Add job_seeker_profile to context using ProfileManager
        user = cast(AuthenticatedUser, self.request.user)
        context["job_seeker_profile"] = ProfileManager.get_profile_for_user(user)
        context["email_verified"] = EmailAddress.objects.filter(
            user=user, email=user.email, verified=True
        ).exists()

        return context
