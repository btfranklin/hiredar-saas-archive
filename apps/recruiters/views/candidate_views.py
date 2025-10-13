"""Views for recruiter interactions with candidate profiles."""

from typing import Any, cast

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import redirect
from django.views.generic import DetailView

from apps.authentication.types import AuthenticatedUser
from apps.job_seekers.models import JobSeekerProfile


class CandidateResumeView(LoginRequiredMixin, DetailView):
    """
    Allow recruiters to view the full resume for a candidate profile.

    Access is granted when:
    1. The requesting user is a recruiter.
    2. The profile belongs to one of the recruiter's candidate pools.
    """

    model = JobSeekerProfile
    template_name = "recruiters/candidate_resume.html"
    context_object_name = "profile"

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        """Restrict access to recruiters who own the candidate pool."""
        user = cast(AuthenticatedUser, request.user)

        if user.user_type != "recruiter":
            messages.error(request, "Only recruiters can view candidate resumes.")
            return redirect("core:home")

        profile = self.get_object()

        if profile.candidate_pool and profile.candidate_pool.recruiter == user:
            return super().dispatch(request, *args, **kwargs)

        messages.error(
            request,
            "This resume is not available outside of your candidate pools.",
        )
        return redirect("recruiters:dashboard")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add related conversation/job opening placeholders to the context."""
        context = super().get_context_data(**kwargs)
        context.setdefault("conversation", None)
        context.setdefault("job_opening", None)
        return context
