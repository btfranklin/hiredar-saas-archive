from typing import ClassVar

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView

from apps.authentication.types import AuthenticatedUser
from apps.recruiters.models import JobOpening


class JobOpeningDetailView(LoginRequiredMixin, DetailView):
    """Read-only job-opening detail page for job seekers."""

    model: ClassVar[type[JobOpening]] = JobOpening
    template_name: str = "job_seekers/job_openings/detail.html"
    context_object_name = "job_opening"

    def dispatch(self, request, *args, **kwargs):
        user: AuthenticatedUser = request.user  # type: ignore
        # Only allow authenticated job-seekers (or anonymous? decide). Recruiters have their own page.
        if not user.is_authenticated or user.user_type != "job_seeker":
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Job-seekers can see only active job openings.
        return JobOpening.objects.filter(status="active")
