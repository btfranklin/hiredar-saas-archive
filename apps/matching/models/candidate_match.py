"""Candidate match model."""

from __future__ import annotations

from decimal import Decimal

from django.db import models


class CandidateMatch(models.Model):
    """Match between a talent sheet and a job opening."""

    job_opening = models.ForeignKey(
        "recruiters.JobOpening",
        on_delete=models.CASCADE,
        related_name="candidate_matches",
    )
    talent_sheet = models.ForeignKey(
        "job_seekers.TalentSheet",
        on_delete=models.CASCADE,
        related_name="job_matches",
    )
    holistic_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.0"),
        help_text="Holistic similarity score (0-1)",
    )
    skills_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.0"),
        help_text="Skills similarity score (0-1)",
    )
    experience_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.0"),
        help_text="Experience similarity score (0-1)",
    )
    wildcard_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.0"),
        help_text="Wildcard similarity score (0-1)",
    )
    qualifications_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.0"),
        help_text="Qualifications similarity score (0-1)",
    )
    status = models.CharField(
        max_length=20,
        choices=(
            ("identified", "Identified"),
            ("open", "Open"),
            ("contacted", "Contacted"),
            ("candidate_interested", "Candidate Interested"),
            ("candidate_declined", "Candidate Declined"),
            ("recruiter_rejected", "Recruiter Rejected"),
        ),
        default="identified",
    )
    is_analyzed = models.BooleanField(
        default=False,
        help_text="Whether this match has been analyzed by AI",
    )
    match_summary = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="A headline summarizing why this is a good match",
    )
    match_analysis = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed analysis of why this job and candidate match",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "matching"
        unique_together = ["job_opening", "talent_sheet"]

    def __str__(self) -> str:
        current_type = getattr(self, "match_type", "holistic")

        match_type_display = {
            "holistic": "Holistic Match",
            "skills": "Skills Match",
            "experience": "Experience Match",
            "wildcard": "Wildcard Match",
            "qualifications": "Qualifications Match",
        }.get(current_type, current_type)

        job_seeker_profile = self.talent_sheet.job_seeker
        job_owner = job_seeker_profile.user_owner
        job_seeker_name = (
            job_owner.get_full_name()
            if job_owner
            else f"Profile {job_seeker_profile.pk}"
        )
        return (
            f"{job_seeker_name} - {self.job_opening} "
            f"({self.get_score_for_type():.2f}, {match_type_display})"
        )

    @property
    def holistic_rating(self) -> int:
        return self._score_to_rating(self.holistic_score)

    @property
    def skills_rating(self) -> int:
        return self._score_to_rating(self.skills_score)

    @property
    def experience_rating(self) -> int:
        return self._score_to_rating(self.experience_score)

    @property
    def wildcard_rating(self) -> int:
        return self._score_to_rating(self.wildcard_score)

    @property
    def qualifications_rating(self) -> int:
        return self._score_to_rating(self.qualifications_score)

    def _score_to_rating(self, score: Decimal) -> int:
        float_score = float(score)
        if float_score < 0.5:
            return max(1, round(float_score * 10))
        return min(10, 5 + round((float_score - 0.5) * 10))

    def get_score_for_type(self) -> Decimal:
        current_type = getattr(self, "match_type", "holistic")

        if current_type == "holistic":
            return self.holistic_score
        if current_type == "skills":
            return self.skills_score
        if current_type == "experience":
            return self.experience_score
        if current_type == "wildcard":
            return self.wildcard_score
        if current_type == "qualifications":
            return self.qualifications_score
        return Decimal("0.0")

    def get_rating_for_type(self) -> int:
        current_type = getattr(self, "match_type", "holistic")

        if current_type == "holistic":
            return self.holistic_rating
        if current_type == "skills":
            return self.skills_rating
        if current_type == "experience":
            return self.experience_rating
        if current_type == "wildcard":
            return self.wildcard_rating
        if current_type == "qualifications":
            return self.qualifications_rating
        return 1

    def get_all_match_ratings(self) -> list[tuple[str, str, int]]:
        return [
            ("holistic", "Holistic", self.holistic_rating),
            ("skills", "Skills", self.skills_rating),
            ("experience", "Experience", self.experience_rating),
            ("qualifications", "Qualifications", self.qualifications_rating),
            ("wildcard", "Wildcard", self.wildcard_rating),
        ]
