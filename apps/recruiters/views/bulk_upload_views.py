from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponseBase, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView
from django_q.tasks import async_task

from apps.recruiters.forms import BulkResumeUploadForm
from apps.recruiters.models import BulkResumeUpload
from apps.recruiters.tasks.bulk_resume_tasks import unpack_and_process_zip

# ---------------------------------------------------------------------------
# Create (upload) view
# ---------------------------------------------------------------------------


class BulkResumeUploadView(LoginRequiredMixin, CreateView):
    """Allow recruiters to upload a ZIP of resumes."""

    model = BulkResumeUpload
    form_class = BulkResumeUploadForm
    template_name = "recruiters/bulk_upload.html"
    success_url = reverse_lazy("recruiters:bulk_upload_list")

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        user = request.user
        if not user.is_authenticated or getattr(user, "user_type", "") != "recruiter":
            return redirect("core:home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form: BulkResumeUploadForm):  # type: ignore[override]
        bulk = form.save(commit=False)
        bulk.recruiter = self.request.user.recruiter_profile  # type: ignore[attr-defined]
        bulk.save()
        self.object = bulk  # set object for success_url formatting
        # Schedule background unpack/processing via Django Q
        async_task(unpack_and_process_zip, bulk.pk)
        return HttpResponseRedirect(self.get_success_url())


# ---------------------------------------------------------------------------
# List view
# ---------------------------------------------------------------------------


class BulkResumeUploadListView(LoginRequiredMixin, ListView):
    """Show uploads by the current recruiter."""

    model = BulkResumeUpload
    template_name = "recruiters/bulk_upload_list.html"
    context_object_name = "bulk_uploads"

    def get_queryset(self):  # type: ignore[override]
        user = self.request.user
        return BulkResumeUpload.objects.filter(recruiter=user.recruiter_profile).order_by("-created_at")  # type: ignore[attr-defined]
