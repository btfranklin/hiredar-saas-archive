"""
Django admin configuration for the matching app.

This module defines the admin interfaces for the matching-related models,
providing configuration for how these models are displayed and managed
in the Django admin interface.
"""

from django.contrib import admin

from .models import CandidateMatch


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
