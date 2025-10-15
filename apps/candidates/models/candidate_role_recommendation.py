"""Role recommendation model for candidate profiles."""

from __future__ import annotations

from django.db import models


class CandidateRoleRecommendation(models.Model):
    """
    Stores AI-generated role recommendations for a candidate profile.
    """

    candidate_profile = models.ForeignKey(
        "candidates.CandidateProfile",
        on_delete=models.CASCADE,
        related_name="role_recommendations",
        help_text="Candidate profile this recommendation belongs to",
    )
    role_title = models.CharField(
        max_length=100,
        help_text="Title of the recommended role (e.g. 'Senior Software Engineer')",
    )
    description = models.TextField(
        help_text="Short description outlining responsibilities and value",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp indicating when the recommendation was generated",
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        """
        Human-readable representation used in admin/debug views.
        """
        profile = self.candidate_profile
        pool_name = profile.pool.name if profile and profile.pool else "Unknown Pool"
        display_name = profile.display_name if profile else "Candidate"
        return f"{self.role_title} for {display_name} ({pool_name})"

    @property
    def pool(self):
        """Surface the related candidate pool for convenience."""
        return self.candidate_profile.pool if self.candidate_profile else None
