from django.contrib import admin

from .models import BulkResumeUpload, JobOpening, RecruiterProfile, ResumeFile


@admin.register(RecruiterProfile)
class RecruiterProfileAdmin(admin.ModelAdmin):
    """Admin configuration for RecruiterProfile model."""

    list_display = (
        "user",
        "credits_available",
        "credits_total",
        "total_interest_requests_sent",
        "total_messages_sent",
    )
    list_filter = ()
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
        "status",
        "created_at",
    )
    list_filter = ("status", "job_level", "employment_type", "created_at")
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
        ("Status", {"fields": ("status",)}),
    )


@admin.register(BulkResumeUpload)
class BulkResumeUploadAdmin(admin.ModelAdmin):
    """Admin for managing resume pools."""

    list_display = (
        "name",
        "recruiter",
        "created_at",
        "processed",
        "total_files",
        "processed_profiles",
    )
    list_filter = ("processed", "created_at")
    search_fields = ("name", "recruiter__user__email")


@admin.register(ResumeFile)
class ResumeFileAdmin(admin.ModelAdmin):
    """Admin for managing individual resumes in pools."""

    list_display = ("original_filename", "bulk_upload", "recruiter", "uploaded_at")
    list_filter = ("uploaded_at",)
    search_fields = ("original_filename", "recruiter__user__email")
