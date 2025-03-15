from django.contrib import admin

from apps.job_seekers.models import JobSeekerProfile


@admin.register(JobSeekerProfile)
class JobSeekerProfileAdmin(admin.ModelAdmin):
    """Admin configuration for JobSeekerProfile model."""

    list_display = ("user", "current_position", "desired_role", "years_of_experience")
    list_filter = ("years_of_experience",)
    search_fields = (
        "user__email",
        "user__name",
        "skills",
        "current_position",
    )
    fieldsets = (
        (None, {"fields": ("user",)}),
        (
            "Profile Information",
            {
                "fields": (
                    "current_position",
                    "desired_role",
                    "years_of_experience",
                    "professional_summary",
                    "phone",
                )
            },
        ),
        (
            "Skills & Experience",
            {"fields": ("skills", "experience", "education", "certifications")},
        ),
        ("Social Links", {"fields": ("linkedin_url", "github_url", "portfolio_url")}),
        ("Resume Data", {"fields": ("resume_xml",), "classes": ("collapse",)}),
    )
