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

    Configures the admin interface for managing matches between candidate profiles
    and job openings, including display fields and filtering options.
    """

    list_display = (
        "job_opening",
        "candidate_profile",
        "get_score_for_type",
        "status",
        "is_analyzed",
        "created_at",
    )
    list_filter = (
        "status",
        "is_analyzed",
        "created_at",
    )
    search_fields = (
        "job_opening__title",
        "candidate_profile__pool__recruiter__email",
        "match_summary",
    )
    readonly_fields = ("created_at", "updated_at")

    def get_score_for_type(self, obj):
        """Display holistic score by default when browsing in admin."""
        return f"{float(obj.holistic_score):.4f}"

    get_score_for_type.short_description = "Holistic Score"
    get_score_for_type.admin_order_field = "holistic_score"
