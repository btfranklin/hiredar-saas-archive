"""
Django admin configuration for the jobs app.

This module defines the admin interfaces for the job-related models,
providing configuration for how these models are displayed and managed
in the Django admin interface.
"""

from django.contrib import admin

from .models import CandidateMatch, JobOpening


@admin.register(JobOpening)
class JobOpeningAdmin(admin.ModelAdmin):
    """
    Admin configuration for JobOpening model.

    Defines how job openings are displayed and managed in the Django admin,
    including display fields, filters, and search capabilities.
    """

    list_display = ("title", "recruiter", "location", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("title", "description", "required_skills")


@admin.register(CandidateMatch)
class CandidateMatchAdmin(admin.ModelAdmin):
    """
    Admin configuration for CandidateMatch model.

    Configures the admin interface for managing matches between job seekers
    and job openings, including display fields and filtering options.
    """

    list_display = (
        "job_opening",
        "job_seeker",
        "match_score",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("job_opening__title", "job_seeker__user__email")
