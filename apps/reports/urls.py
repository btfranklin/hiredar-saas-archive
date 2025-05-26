"""
URL patterns for the reports app.

This module defines the URL routes for report generation functionality.
"""

from django.urls import path

from apps.reports.views import export_csv, export_pdf

app_name = "reports"

urlpatterns = [
    path("jobs/<int:job_id>/export/csv/", export_csv, name="export_csv"),
    path("jobs/<int:job_id>/export/pdf/", export_pdf, name="export_pdf"),
]
