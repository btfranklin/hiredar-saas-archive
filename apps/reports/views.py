"""
Views for generating and serving reports.

This module contains views for generating CSV and PDF reports
for candidate matches on job openings.
"""

from typing import cast

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404

from apps.authentication.types import AuthenticatedUser
from apps.recruiters.models import JobOpening
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

    # Generate CSV
    csv_data = generate_csv(job, limit=limit_int)

    # Create response
    filename = get_export_filename(job, "csv")
    response = HttpResponse(csv_data, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    job.recruiter.total_shortlist_csvs_generated += 1
    job.recruiter.save(update_fields=["total_shortlist_csvs_generated"])

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

    # Generate PDF
    pdf_data = generate_pdf(job, limit=limit_int)

    # Create response
    filename = get_export_filename(job, "pdf")
    response = HttpResponse(pdf_data, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    job.recruiter.total_shortlist_pdfs_generated += 1
    job.recruiter.save(update_fields=["total_shortlist_pdfs_generated"])

    return response
