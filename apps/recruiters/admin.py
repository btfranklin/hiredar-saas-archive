from django.contrib import admin

from .models import JobOpening, RecruiterProfile


@admin.register(RecruiterProfile)
class RecruiterProfileAdmin(admin.ModelAdmin):
    """Admin configuration for RecruiterProfile model."""

    list_display = ("user", "subscription_tier")
    list_filter = ("subscription_tier",)
    search_fields = ("user__email", "user__name")


@admin.register(JobOpening)
class JobOpeningAdmin(admin.ModelAdmin):
    """
    Admin configuration for JobOpening model.

    Defines how job openings are displayed and managed in the Django admin,
    including display fields, filters, and search capabilities.
    """

    list_display = (
        "title",
        "company",
        "job_level",
        "location",
        "employment_type",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "job_level", "employment_type", "created_at")
    search_fields = ("title", "description", "company", "required_skills", "location")

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("recruiter", "title", "description", "company", "location")},
        ),
        ("Job Classification", {"fields": ("job_level", "employment_type")}),
        (
            "Compensation & Benefits",
            {"fields": ("salary_min", "salary_max", "benefits", "additional_perks")},
        ),
        (
            "Qualifications & Skills",
            {"fields": ("required_skills", "required_qualifications", "soft_skills")},
        ),
        (
            "Job Details",
            {"fields": ("responsibilities", "daily_tasks", "performance_expectations")},
        ),
        (
            "Working Conditions",
            {
                "fields": (
                    "working_hours",
                    "work_environment",
                    "reporting_to",
                    "travel_requirements",
                )
            },
        ),
        ("Status", {"fields": ("is_active",)}),
    )
