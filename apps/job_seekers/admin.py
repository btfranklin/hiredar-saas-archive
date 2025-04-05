from django.contrib import admin, messages
from django.db.models import Q
from django_q.tasks import async_task

from apps.job_seekers.models import JobSeekerProfile, RoleRecommendation, TalentSheet


class InTalentPoolFilter(admin.SimpleListFilter):
    """Filter for job seekers in the talent pool."""

    title = "Talent Pool Status"
    parameter_name = "in_talent_pool"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Active"),
            ("no", "Inactive"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(talent_sheet__is_published=True)
        if self.value() == "no":
            return queryset.filter(
                Q(talent_sheet__isnull=True) | Q(talent_sheet__is_published=False)
            )
        return queryset


@admin.register(JobSeekerProfile)
class JobSeekerProfileAdmin(admin.ModelAdmin):
    """Admin configuration for JobSeekerProfile model."""

    list_display = (
        "user",
        "get_name",
        "most_recent_title",
        "location",
        "in_talent_pool",
    )
    list_filter = (InTalentPoolFilter,)
    search_fields = (
        "user__email",
        "user__name",
        "skills",
        "most_recent_title",
        "location",
    )
    actions = ["enter_talent_pool", "leave_talent_pool"]

    def get_name(self, obj):
        """Get the name of the user."""
        return obj.user.name if obj.user else ""

    get_name.short_description = "Name"
    get_name.admin_order_field = "user__name"

    def enter_talent_pool(self, request, queryset):
        """Add selected job seekers to the talent pool."""
        count = 0
        errors = 0
        for profile in queryset:
            if not profile.resume_xml:
                messages.warning(
                    request, f"Skipped {profile.user.email}: No resume data available"
                )
                errors += 1
                continue

            # Queue the talent sheet generation task
            async_task(
                "apps.job_seekers.tasks.talent_sheet_tasks.generate_talent_sheet_task",
                profile.id,
                task_name=f"generate_talent_sheet_{profile.id}",
            )
            count += 1

        if count:
            messages.success(
                request,
                f"Queued {count} job seeker(s) for talent pool entry. Talent sheets will be generated in the background.",
            )
        if errors:
            messages.warning(
                request, f"Skipped {errors} job seeker(s) due to missing resume data."
            )

    enter_talent_pool.short_description = "Add selected job seekers to talent pool"

    def leave_talent_pool(self, request, queryset):
        """Remove selected job seekers from the talent pool."""
        count = 0
        for profile in queryset:
            # Unpublish any existing talent sheet
            talent_sheet = getattr(profile, "talent_sheet", None)
            if talent_sheet:
                talent_sheet.is_published = False
                talent_sheet.save(update_fields=["is_published"])
                count += 1

        if count:
            messages.success(
                request, f"Removed {count} job seeker(s) from the talent pool."
            )
        else:
            messages.info(request, "No job seekers were in the talent pool.")

    leave_talent_pool.short_description = "Remove selected job seekers from talent pool"

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
                    "location",
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

    list_display = (
        "job_seeker",
        "get_job_seeker_name",
        "is_published",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_published", "created_at", "updated_at")
    search_fields = ("job_seeker__user__email", "job_seeker__user__name", "ideal_roles")

    def get_job_seeker_name(self, obj):
        """Get the name of the job seeker."""
        return (
            obj.job_seeker.user.name if obj.job_seeker and obj.job_seeker.user else ""
        )

    get_job_seeker_name.short_description = "Name"
    get_job_seeker_name.admin_order_field = "job_seeker__user__name"

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
        ("Salary Expectations", {"fields": ("salary_min",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ("created_at", "updated_at")
