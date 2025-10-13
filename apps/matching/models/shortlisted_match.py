"""Shortlisted candidate match model."""

from __future__ import annotations

from django.db import models


class ShortlistedMatch(models.Model):
    """Candidate match shortlisted for a job opening."""

    job_opening = models.ForeignKey(
        "recruiters.JobOpening",
        on_delete=models.CASCADE,
        related_name="shortlisted_matches",
    )
    candidate_match = models.ForeignKey(
        "matching.CandidateMatch",
        on_delete=models.CASCADE,
        related_name="shortlists",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "matching"
        unique_together = ["job_opening", "candidate_match"]

    def __str__(self) -> str:
        job_title = self.job_opening.title
        seeker_name = (
            self.candidate_match.talent_sheet.job_seeker.user_owner.get_full_name()
            if self.candidate_match.talent_sheet.job_seeker.user_owner
            else f"Profile {self.candidate_match.talent_sheet.job_seeker.pk}"
        )
        return f"Shortlist • {seeker_name} for {job_title}"

    @property
    def holistic_rating(self) -> int:
        return self.candidate_match.holistic_rating
