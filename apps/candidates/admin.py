"""Admin registrations for candidate models."""

from __future__ import annotations

from django.contrib import admin, messages

from apps.candidates.models import CandidatePool, CandidateProfile, CandidateRoleRecommendation
from apps.candidates.services.profile_service import CandidateProfileService
from apps.candidates.tasks.profile_enrichment_tasks import (
    generate_profile_enrichment_task,
)
from apps.core.tasks import safe_async_task

async_task = safe_async_task


class CandidatePoolFilter(admin.SimpleListFilter):
    """Filter profiles by their candidate pool."""

    title = "Candidate Pool"
    parameter_name = "candidate_pool"

    def lookups(self, request, model_admin):  # type: ignore[override]
        pools = CandidatePool.objects.all().order_by("name")
        return [(pool.pk, pool.name) for pool in pools]

    def queryset(self, request, queryset):  # type: ignore[override]
        if not self.value():
            return queryset
        return queryset.filter(pool__pk=self.value())


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    """Admin configuration for CandidateProfile."""

    list_display = (
        "display_name",
        "most_recent_title",
        "location",
        "is_published",
        "pool",
    )
    list_filter = (CandidatePoolFilter, "is_published", "created_at")
    search_fields = ("candidate_name", "most_recent_title", "skills")
    actions = ["publish_profiles", "unpublish_profiles"]

    def publish_profiles(self, request, queryset):  # type: ignore[override]
        queued = 0
        skipped = 0

        for profile in queryset:
            if not profile.resume_xml:
                skipped += 1
                continue
            async_task(
                generate_profile_enrichment_task,
                profile.pk,
                task_name=f"publish_candidate_profile_{profile.pk}",
                timeout=300,
            )
            queued += 1

        if queued:
            messages.success(
                request,
                f"Queued {queued} candidate profile(s) for enrichment.",
            )
        if skipped:
            messages.warning(
                request,
                f"Skipped {skipped} profile(s) due to missing resume data.",
            )

    publish_profiles.short_description = "Publish selected candidate profiles"

    def unpublish_profiles(self, request, queryset):  # type: ignore[override]
        updated = 0
        for profile in queryset:
            CandidateProfileService.safe_update_publication_status(
                profile.pk, is_published=False
            )
            updated += 1
        if updated:
            messages.success(
                request, f"Unpublished {updated} candidate profile(s)."
            )

    unpublish_profiles.short_description = "Unpublish selected candidate profiles"

    fieldsets = (
        (None, {"fields": ("pool", "is_published")}),
        (
            "Profile Information",
            {
                "fields": (
                    "candidate_name",
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
        (
            "Recruiter-Facing Content",
            {
                "fields": (
                    "personal_tagline",
                    "promotional_blurb",
                    "experience_overview",
                    "ideal_roles",
                    "qualifications",
                )
            },
        ),
        ("Resume Data", {"fields": ("resume_xml",), "classes": ("collapse",)}),
    )


@admin.register(CandidateRoleRecommendation)
class CandidateRoleRecommendationAdmin(admin.ModelAdmin):
    """List role recommendations produced for candidate profiles."""

    list_display = ("candidate_profile", "role_title", "pool", "created_at")
    list_filter = ("created_at", CandidatePoolFilter)
    search_fields = ("role_title", "candidate_profile__candidate_name")

    def pool(self, obj):  # type: ignore[override]
        return obj.pool
