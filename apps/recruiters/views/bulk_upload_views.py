import uuid
from typing import Any, cast
from zipfile import ZipFile

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBase,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, TemplateView, View

from apps.authentication.types import AuthenticatedUser
from apps.core.tasks import safe_async_task
from apps.job_seekers.models.profile import CandidatePool, JobSeekerProfile
from apps.job_seekers.models.talent import TalentSheet
from apps.recruiters.forms import BulkResumeUploadForm
from apps.recruiters.models import BulkResumeUpload
from apps.recruiters.tasks.bulk_resume_tasks import unpack_and_process_zip

async_task = safe_async_task


class BulkResumeUploadView(LoginRequiredMixin, CreateView):
    """Allow recruiters to upload a ZIP of resumes."""

    model = BulkResumeUpload
    form_class = BulkResumeUploadForm
    template_name = "recruiters/bulk_upload.html"
    success_url = reverse_lazy("recruiters:dashboard")

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

        # Save bulk upload first
        bulk.save()
        self.object = bulk

        # ----------------------------------------------------------
        # 1. Create an empty CandidatePool so the dashboard can show
        #    a card immediately.
        # 2. Insert a placeholder TaskMeta so the card displays a
        #    spinner while the ZIP is being unpacked.
        # ----------------------------------------------------------

        candidate_pool = CandidatePool.objects.create(
            recruiter=bulk.recruiter.user,  # ``CandidatePool`` expects a User instance
            name=bulk.name,
        )

        from apps.core.models import TaskMeta  # local import to avoid circular deps

        placeholder_meta = TaskMeta.objects.create(
            queue_id=f"import-{bulk.pk}",
            name="Importing resumes",
            owner=bulk.recruiter.user,
            content_object=candidate_pool,
            state=TaskMeta.State.PENDING,
        )

        # Schedule asynchronous unpacking, passing the pool id and placeholder meta pk
        async_task(
            unpack_and_process_zip,
            bulk.pk,
            candidate_pool.pk,
            str(placeholder_meta.pk),
            task_name=f"unpack_and_process_zip_{bulk.pk}",
        )

        # Notify recruiter that bulk upload succeeded and is processing
        messages.success(self.request, "Bulk upload succeeded and is processing.")
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


class CandidatePoolListView(LoginRequiredMixin, ListView):
    """List view for all candidate pools belonging to the recruiter, displayed as cards."""

    model = CandidatePool  # type: ignore[name-defined]
    template_name = "recruiters/candidate_pool_list.html"
    context_object_name = "candidate_pools"

    def get_queryset(self):  # type: ignore[override]
        user = cast(AuthenticatedUser, self.request.user)
        return CandidatePool.objects.filter(
            recruiter=user  # type: ignore[attr-defined]
        ).order_by("-created_at")


class CandidatePoolDetailView(LoginRequiredMixin, DetailView):
    """Detail view for a processed candidate pool."""

    model = CandidatePool  # type: ignore[name-defined]
    template_name = "recruiters/candidate_pool_detail.html"
    context_object_name = "pool"

    def get_queryset(self):  # type: ignore[override]
        user = cast(AuthenticatedUser, self.request.user)
        return CandidatePool.objects.filter(
            recruiter=user  # type: ignore[attr-defined]
        )

    # ------------------------------------------------------------------
    # Inline rename support (HTMX or full-form POST)
    # ------------------------------------------------------------------

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:  # type: ignore[override]
        """Handle inline rename submissions.

        Expected POST payload: ``name`` – the new pool name.

        Behaviour:
        * Update the object and return either an HTMX fragment (just the <h1>)
          or redirect back to GET depending on request headers.
        """

        self.object = self.get_object()  # type: ignore[assignment]
        new_name = request.POST.get("name", "").strip()
        if new_name:
            self.object.name = new_name
            self.object.save(update_fields=["name"])

        # HTMX: return only the heading so the client can swap it in place
        if request.headers.get("HX-Request"):
            return HttpResponse(
                f'<h1 id="pool-name-{self.object.pk}" class="text-2xl font-bold flex items-center gap-2">'
                f"{self.object.name}</h1>",
                content_type="text/html",
            )

        # Fallback full-page redirect
        return redirect("recruiters:candidate_pool_detail", pk=self.object.pk)


class CandidatePoolDeleteView(LoginRequiredMixin, View):
    """Handle deletion of a processed candidate pool via POST."""

    def post(
        self, request: HttpRequest, pk: int, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        user = cast(AuthenticatedUser, request.user)
        pool = get_object_or_404(
            CandidatePool,
            pk=pk,
            recruiter=user,  # type: ignore[attr-defined]
        )
        # Deleting this pool cascades deletion of related profiles
        pool.delete()
        # If request is via HTMX, remove the card without redirecting
        if request.headers.get("HX-Request"):
            return HttpResponse(status=204)
        # Fallback full-page redirect
        return redirect("recruiters:candidate_pool_list")


class CandidatePoolTalentSheetDetailView(LoginRequiredMixin, TemplateView):
    """Detail view for a talent sheet of a candidate in a candidate pool."""

    template_name = "recruiters/talent_sheet_detail.html"

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        # Only recruiters can access candidate talent sheets
        user = request.user
        if not user.is_authenticated or getattr(user, "user_type", "") != "recruiter":
            return redirect("core:home")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        # Load the candidate profile ensuring it belongs to this recruiter's pool
        profile_id = self.kwargs.get("pk")
        profile = get_object_or_404(
            JobSeekerProfile,
            pk=profile_id,
            candidate_pool__recruiter=self.request.user,  # type: ignore[attr-defined]
        )
        context["profile"] = profile
        # Include talent sheet if generated
        try:
            talent_sheet = TalentSheet.objects.get(job_seeker=profile)
            context["talent_sheet"] = talent_sheet
            context["has_talent_sheet"] = True
        except TalentSheet.DoesNotExist:
            context["talent_sheet"] = None
            context["has_talent_sheet"] = False
        # Include pool for navigation
        context["pool"] = profile.candidate_pool
        return context
