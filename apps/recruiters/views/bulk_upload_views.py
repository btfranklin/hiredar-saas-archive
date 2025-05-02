from typing import Any, cast
from zipfile import ZipFile

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBase,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, View

from apps.authentication.types import AuthenticatedUser
from apps.core.tasks import safe_async_task
from apps.recruiters.forms import BulkResumeUploadForm
from apps.recruiters.models import BulkResumeUpload
from apps.recruiters.tasks.bulk_resume_tasks import unpack_and_process_zip

async_task = safe_async_task


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
        # Prepare bulk upload without saving to check credits
        bulk = form.save(commit=False)
        recruiter_profile = self.request.user.recruiter_profile  # type: ignore[attr-defined]
        bulk.recruiter = recruiter_profile

        # Count PDF resumes inside the uploaded ZIP
        uploaded_zip = form.cleaned_data["zip_file"]
        with ZipFile(uploaded_zip) as zf:
            # Count only real PDF files – skip macOS metadata and temp files
            pdf_names: list[str] = []
            for member in zf.namelist():
                member_lower = member.lower()
                if not member_lower.endswith(".pdf"):
                    continue
                # Skip macOS resource-fork entries
                if member_lower.startswith("__macosx/") or "/__macosx/" in member_lower:
                    continue
                # Skip dot-underscore files
                if member_lower.startswith("._") or "/._" in member_lower:
                    continue
                pdf_names.append(member)
            pdf_count = len(pdf_names)

        # Ensure recruiter has enough credits
        credits_available = recruiter_profile.credits_available
        if pdf_count > credits_available:
            error_message = f"Insufficient credits: you have {credits_available} credits but uploaded {pdf_count} resumes."
            # If HTMX request, return an error fragment with Buy More Credits button
            if self.request.headers.get("HX-Request"):
                return render(
                    self.request,
                    "recruiters/partials/credit_error.html",
                    {
                        "message": error_message,
                        "credits_url": reverse("recruiters:credits"),
                    },
                    status=200,
                )
            # Otherwise, attach to form errors in full page
            form.add_error("zip_file", error_message)
            return self.form_invalid(form)

        # Deduct credits up-front
        recruiter_profile.credits_available = credits_available - pdf_count
        recruiter_profile.save(update_fields=["credits_available"])

        # Save bulk upload and schedule processing
        bulk.save()
        self.object = bulk
        async_task(unpack_and_process_zip, bulk.pk)
        # If this is an HTMX request, instruct client to redirect to list view
        success_url = self.get_success_url()
        if self.request.headers.get("HX-Request"):
            response = HttpResponse(status=200)
            response["HX-Redirect"] = success_url
            return response
        return HttpResponseRedirect(success_url)

    def form_invalid(
        self, form: BulkResumeUploadForm
    ):  # HTMX-aware invalid form handling
        # If this is an HTMX request, return only the form container snippet with errors
        if self.request.headers.get("HX-Request"):
            return render(
                self.request,
                "recruiters/partials/bulk_upload_form.html",
                {"form": form},
                status=200,
            )
        # Fallback to default full-page form invalid handling
        return super().form_invalid(form)


class BulkResumeUploadListView(LoginRequiredMixin, ListView):
    """Show uploads by the current recruiter."""

    model = BulkResumeUpload
    template_name = "recruiters/bulk_upload_list.html"
    context_object_name = "bulk_uploads"

    def get_queryset(self):  # type: ignore[override]
        user = cast(AuthenticatedUser, self.request.user)
        return BulkResumeUpload.objects.filter(
            recruiter=user.recruiter_profile  # type: ignore[attr-defined]
        ).order_by("-created_at")


class BulkResumeUploadDetailView(LoginRequiredMixin, DetailView):
    """Detail view for a single resume pool."""

    model = BulkResumeUpload
    template_name = "recruiters/bulk_upload_detail.html"
    context_object_name = "pool"

    def get_queryset(self):
        # Ensure recruiters only see their own pools
        user = cast(AuthenticatedUser, self.request.user)
        return BulkResumeUpload.objects.filter(
            recruiter=user.recruiter_profile  # type: ignore[attr-defined]
        )


class BulkResumeUploadDeleteView(LoginRequiredMixin, View):
    """Handle deletion of a resume pool via POST."""

    def post(
        self, request: HttpRequest, pk: int, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        user = cast(AuthenticatedUser, request.user)
        pool = get_object_or_404(
            BulkResumeUpload,
            pk=pk,
            recruiter=user.recruiter_profile,  # type: ignore[attr-defined]
        )
        # Delete the bulk upload record and its ZIP file
        pool.delete()
        return redirect("recruiters:bulk_upload_list")


class ResumePoolListView(LoginRequiredMixin, ListView):
    """List view for all resume pools belonging to the recruiter, displayed as cards."""

    model = BulkResumeUpload
    template_name = "recruiters/resume_pool_list.html"
    context_object_name = "resume_pools"

    def get_queryset(self):  # type: ignore[override]
        user = cast(AuthenticatedUser, self.request.user)
        return BulkResumeUpload.objects.filter(
            recruiter=user.recruiter_profile  # type: ignore[attr-defined]
        ).order_by("-created_at")
