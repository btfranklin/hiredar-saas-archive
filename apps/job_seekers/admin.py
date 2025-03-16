from django.contrib import admin

from apps.job_seekers.models import JobSeekerProfile, RoleRecommendation


@admin.register(JobSeekerProfile)
class JobSeekerProfileAdmin(admin.ModelAdmin):
    """Admin configuration for JobSeekerProfile model."""

    list_display = ("user", "most_recent_title", "desired_role", "years_of_experience")
    list_filter = ("years_of_experience",)
    search_fields = (
        "user__email",
        "user__name",
        "skills",
        "most_recent_title",
    )
    fieldsets = (
        (None, {"fields": ("user",)}),
        (
            "Profile Information",
            {
                "fields": (
                    "most_recent_title",
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


@admin.register(RoleRecommendation)
class RoleRecommendationAdmin(admin.ModelAdmin):
    """
    Admin configuration for RoleRecommendation model.

    Sets up the admin interface for role recommendations provided to job seekers,
    with appropriate display fields and search functionality.
    """

    list_display = ("job_seeker", "role_title", "confidence_score", "created_at")
    list_filter = ("created_at",)
    search_fields = ("role_title", "job_seeker__user__email")
