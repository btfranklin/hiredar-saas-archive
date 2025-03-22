from django.contrib import admin

from apps.job_seekers.models import JobSeekerProfile, RoleRecommendation, TalentSheet


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

    list_display = ("job_seeker", "role_title", "created_at")
    list_filter = ("created_at",)
    search_fields = ("role_title", "job_seeker__user__email")


@admin.register(TalentSheet)
class TalentSheetAdmin(admin.ModelAdmin):
    """
    Admin configuration for TalentSheet model.

    Provides an interface for viewing and managing AI-generated talent sheets
    for job seekers in the talent pool.
    """

    list_display = ("job_seeker", "is_published", "created_at", "updated_at")
    list_filter = ("is_published", "created_at", "updated_at")
    search_fields = ("job_seeker__user__email", "job_seeker__user__name", "ideal_roles")

    fieldsets = (
        (None, {"fields": ("job_seeker", "is_published")}),
        (
            "Talent Information",
            {
                "fields": (
                    "promotional_blurb",
                    "skill_overview",
                    "ideal_roles",
                )
            },
        ),
        ("Salary Expectations", {"fields": ("salary_min", "salary_max")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ("created_at", "updated_at")
