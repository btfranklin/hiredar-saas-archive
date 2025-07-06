"""
Views for generating and serving reports.

This module contains views for generating CSV and PDF reports
for candidate matches on job openings.
"""

from typing import cast

from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse

from apps.authentication.types import AuthenticatedUser
from apps.recruiters.models import JobOpening, RecruiterProfile
from apps.reports.services import generate_csv, generate_pdf, get_export_filename


@login_required
def export_csv(request: HttpRequest, job_id: int) -> HttpResponse:
    """
    Export candidate matches as CSV.

    Args:
        request: The HTTP request
        job_id: ID of the job opening

    Returns:
        HTTP response with CSV file
    """
    user = cast(AuthenticatedUser, request.user)

    # Get the job opening and ensure the user owns it
    job = get_object_or_404(JobOpening, pk=job_id, recruiter__user=user)

    # Get optional limit parameter
    limit = request.GET.get("limit")
    limit_int = None
    if limit and limit.isdigit():
        limit_int = int(limit)

    # Detect if this is a follow-up request meant to download the file after
    # credits have already been deducted in an earlier HTMX call.
    is_download = request.GET.get("download") == "1"

    if is_download:
        # Generate and return the file without additional credit checks.
        csv_data = generate_csv(job, limit=limit_int)
        filename = get_export_filename(job, "csv")
        response = HttpResponse(csv_data, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    # ----------------------------------------------
    # Credits check + deduction for export action
    # ----------------------------------------------
    recruiter_profile = job.recruiter
    credits_needed = 5

    if recruiter_profile.credits_available < credits_needed:
        error_message = (
            f"Insufficient credits: you have {recruiter_profile.credits_available} "
            f"credits but need {credits_needed} to export your shortlist."
        )

        # HTMX request – return modal dialog HTML
        if request.headers.get("HX-Request"):
            modal_html = render_to_string(
                "recruiters/partials/insufficient_credits_modal.html",
                {
                    "message": error_message,
                    "credits_url": reverse("recruiters:credits"),
                },
                request=request,
            )

            resp = HttpResponse(modal_html, status=200)
            resp["HX-Reswap"] = "afterend"
            return resp

        # Non-HTMX fallback: redirect to credits page with flash message
        response = redirect("recruiters:credits")
        response["Location"] += "?error=insufficient_credits"
        return response

    # Deduct credits and increment counter atomically
    RecruiterProfile.objects.filter(pk=recruiter_profile.pk).update(
        credits_available=F("credits_available") - credits_needed,
        total_shortlist_csvs_generated=F("total_shortlist_csvs_generated") + 1,
    )

    # If this is an HTMX request, instruct the client to perform a browser
    # redirect to trigger the actual file download (which cannot be handled
    # over the XHR connection).
    if request.headers.get("HX-Request"):
        resp = HttpResponse(status=200)
        resp["HX-Redirect"] = (
            reverse("reports:export_csv", args=[job.pk]) + "?download=1"
        )
        return resp

    # Non-HTMX: generate and send the file immediately.
    csv_data = generate_csv(job, limit=limit_int)
    filename = get_export_filename(job, "csv")
    response = HttpResponse(csv_data, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def export_pdf(request: HttpRequest, job_id: int) -> HttpResponse:
    """
    Export candidate matches as PDF.

    Args:
        request: The HTTP request
        job_id: ID of the job opening

    Returns:
        HTTP response with PDF file
    """
    user = cast(AuthenticatedUser, request.user)

    # Get the job opening and ensure the user owns it
    job = get_object_or_404(JobOpening, pk=job_id, recruiter__user=user)

    # Get optional limit parameter
    limit = request.GET.get("limit")
    limit_int = None
    if limit and limit.isdigit():
        limit_int = int(limit)

    # Detect follow-up download request
    is_download = request.GET.get("download") == "1"

    if is_download:
        pdf_data = generate_pdf(job, limit=limit_int)
        filename = get_export_filename(job, "pdf")
        response = HttpResponse(pdf_data, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    # ----------------------------------------------
    # Credits check + deduction for export action
    # ----------------------------------------------
    recruiter_profile = job.recruiter
    credits_needed = 5

    if recruiter_profile.credits_available < credits_needed:
        error_message = (
            f"Insufficient credits: you have {recruiter_profile.credits_available} "
            f"credits but need {credits_needed} to export your shortlist."
        )

        if request.headers.get("HX-Request"):
            modal_html = render_to_string(
                "recruiters/partials/insufficient_credits_modal.html",
                {
                    "message": error_message,
                    "credits_url": reverse("recruiters:credits"),
                },
                request=request,
            )

            resp = HttpResponse(modal_html, status=200)
            resp["HX-Reswap"] = "afterend"
            return resp

        response = redirect("recruiters:credits")
        response["Location"] += "?error=insufficient_credits"
        return response

    # Deduct credits and increment counter atomically
    RecruiterProfile.objects.filter(pk=recruiter_profile.pk).update(
        credits_available=F("credits_available") - credits_needed,
        total_shortlist_pdfs_generated=F("total_shortlist_pdfs_generated") + 1,
    )

    if request.headers.get("HX-Request"):
        resp = HttpResponse(status=200)
        resp["HX-Redirect"] = (
            reverse("reports:export_pdf", args=[job.pk]) + "?download=1"
        )
        return resp

    # Non-HTMX: send file directly
    pdf_data = generate_pdf(job, limit=limit_int)
    filename = get_export_filename(job, "pdf")
    response = HttpResponse(pdf_data, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
