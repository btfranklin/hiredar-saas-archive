from django.contrib import admin

from .models import JobOpening, RecruiterProfile


@admin.register(RecruiterProfile)
class RecruiterProfileAdmin(admin.ModelAdmin):
    """Admin configuration for RecruiterProfile model."""

    list_display = ("user", "is_subscribed", "subscription_tier")
    list_filter = ("is_subscribed", "subscription_tier")
    search_fields = ("user__email", "user__name")


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
