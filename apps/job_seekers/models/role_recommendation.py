"""Role recommendation model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:  # pragma: no cover - used for typing only
    from apps.candidates.models import CandidatePool


class RoleRecommendation(models.Model):
    """
    Stores AI-generated role recommendations for job seekers based on their skills and experience.
    """

    job_seeker = models.ForeignKey(
        "job_seekers.JobSeekerProfile",
        on_delete=models.CASCADE,
        related_name="role_recommendations",
        help_text="The job seeker this role recommendation is for",
    )
    role_title = models.CharField(
        max_length=100,
        help_text="The title of the recommended role, in title case (e.g., 'Senior Software Engineer')",
    )
    description = models.TextField(
        help_text="A concise description of the role, outlining key responsibilities and value proposition",
    )
    is_candidate_interested = models.BooleanField(
        default=False,
        help_text="Indicates whether the job seeker has expressed interest in this role",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this recommendation was generated",
    )

    def __str__(self) -> str:
        user_name = (
            self.job_seeker.user_owner.get_full_name()
            if self.job_seeker.user_owner
            else f"Profile {self.job_seeker.pk}"
        )
        return f"{self.role_title} for {user_name}"

    @property
    def candidate_pool(self) -> CandidatePool | None:
        """Access the candidate pool through the job_seeker relationship."""
        return self.job_seeker.candidate_pool if self.job_seeker else None
