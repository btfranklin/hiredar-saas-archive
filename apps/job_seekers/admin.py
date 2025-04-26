from django.contrib import admin, messages
from django.db.models import Q

from apps.authentication.models import User
from apps.core.tasks import safe_async_task
from apps.job_seekers.models import (
    JobSeekerProfile,
    RoleRecommendation,
    TalentSheet,
    UploadedResumePool,
)

async_task = safe_async_task


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


class OwnerTypeFilter(admin.SimpleListFilter):
    """Filter for job seekers by owner type (User or ResumePool)."""

    title = "Owner Type"
    parameter_name = "owner_type"

    def lookups(self, request, model_admin):
        return (
            ("user", "User Account"),
            ("pool", "Resume Pool"),
        )

    def queryset(self, request, queryset):
        from django.contrib.contenttypes.models import ContentType

        user_type = ContentType.objects.get_for_model(User)
        pool_type = ContentType.objects.get_for_model(UploadedResumePool)

        if self.value() == "user":
            return queryset.filter(owner_content_type=user_type)
        if self.value() == "pool":
            return queryset.filter(owner_content_type=pool_type)
        return queryset


class ResumePoolFilter(admin.SimpleListFilter):
    """Filter for objects by their associated resume pool."""

    title = "Resume Pool"
    parameter_name = "resume_pool"

    def lookups(self, request, model_admin):
        # Get all pools
        pools = UploadedResumePool.objects.all().order_by("name")
        return [(pool.pk, pool.name) for pool in pools]

    def queryset(self, request, queryset):
        if not self.value():
            return queryset

        # Use a custom filter based on the model
        if self.value():
            # For RoleRecommendation and TalentSheet, we need to filter through job_seeker
            from django.contrib.contenttypes.models import ContentType

            pool_type = ContentType.objects.get_for_model(UploadedResumePool)

            return queryset.filter(
                job_seeker__owner_content_type=pool_type,
                job_seeker__owner_object_id=self.value(),
            )
        return queryset


@admin.register(JobSeekerProfile)
class JobSeekerProfileAdmin(admin.ModelAdmin):
    """Admin configuration for JobSeekerProfile model."""

    list_display = (
        "get_owner_display",
        "get_name",
        "most_recent_title",
        "location",
        "in_talent_pool",
    )
    list_filter = (InTalentPoolFilter, OwnerTypeFilter)
    search_fields = (
        "most_recent_title",
        "location",
        "skills",
    )
    actions = ["enter_talent_pool", "leave_talent_pool"]

    def get_owner_display(self, obj):
        """Get a display representation of the owner."""
        if obj.user_owner:
            return f"User: {obj.user_owner.email}"
        if obj.uploaded_resume_pool:
            return f"Pool: {obj.uploaded_resume_pool.name}"
        return "Unknown"

    get_owner_display.short_description = "Owner"

    def get_name(self, obj):
        """Get the name of the owner."""
        if obj.user_owner:
            return obj.user_owner.name
        return ""

    get_name.short_description = "Name"

    def enter_talent_pool(self, request, queryset):
        """Add selected job seekers to the talent pool."""
        count = 0
        errors = 0
        for profile in queryset:
            if not profile.resume_xml:
                owner_display = self.get_owner_display(profile)
                messages.warning(
                    request, f"Skipped {owner_display}: No resume data available"
                )
                errors += 1
                continue

            # Queue the talent sheet generation task
            async_task(
                "apps.job_seekers.tasks.talent_sheet_tasks.generate_talent_sheet_task",
                profile.pk,
                task_name=f"generate_talent_sheet_{profile.pk}",
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
        (None, {"fields": ("owner_content_type", "owner_object_id")}),
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

    list_display = ("job_seeker", "role_title", "get_owner_display", "created_at")
    list_filter = ("created_at", ResumePoolFilter)
    search_fields = ("role_title",)

    def get_owner_display(self, obj):
        """Get a display representation of the job seeker's owner."""
        if obj.job_seeker.user_owner:
            return f"User: {obj.job_seeker.user_owner.email}"
        if obj.job_seeker.uploaded_resume_pool:
            return f"Pool: {obj.job_seeker.uploaded_resume_pool.name}"
        return "Unknown"

    get_owner_display.short_description = "Owner"


@admin.register(TalentSheet)
class TalentSheetAdmin(admin.ModelAdmin):
    """
    Admin configuration for TalentSheet model.

    Provides an interface for viewing and managing AI-generated talent sheets
    for job seekers in the talent pool.
    """

    list_display = (
        "job_seeker",
        "get_owner_display",
        "is_published",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_published", "created_at", "updated_at", ResumePoolFilter)
    search_fields = ("ideal_roles",)

    def get_owner_display(self, obj):
        """Get a display representation of the job seeker's owner."""
        if obj.job_seeker.user_owner:
            return f"User: {obj.job_seeker.user_owner.email}"
        if obj.job_seeker.uploaded_resume_pool:
            return f"Pool: {obj.job_seeker.uploaded_resume_pool.name}"
        return "Unknown"

    get_owner_display.short_description = "Owner"

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
