"""
Models for the matching app.

This module defines the models for handling candidate matching.
"""

from decimal import Decimal

from django.db import models


class CandidateMatch(models.Model):
    """
    Model for matching talent sheets to job openings.

    Represents a potential match between a talent sheet and job opening,
    with metadata about the quality of the match and its current status.
    """

    job_opening = models.ForeignKey(
        "recruiters.JobOpening",
        on_delete=models.CASCADE,
        related_name="candidate_matches",
    )
    talent_sheet = models.ForeignKey(
        "job_seekers.TalentSheet",
        on_delete=models.CASCADE,  # When a talent sheet is deleted, delete the match
        related_name="job_matches",
    )
    match_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.0"),
        help_text="Match score between 0 and 100",
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
    match_type = models.CharField(
        max_length=20,
        choices=(
            ("holistic", "Holistic Match"),
            ("skills", "Skills Match"),
            ("experience", "Experience Match"),
            ("wildcard", "Wildcard Match"),
        ),
        default="holistic",
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
        # Ensure we don't have duplicate matches for the same job opening, talent sheet, and match type
        unique_together = ["job_opening", "talent_sheet", "match_type"]

    def __str__(self) -> str:
        # Simple approach to avoid linter errors
        match_type_display = {
            "holistic": "Holistic Match",
            "skills": "Skills Match",
            "experience": "Experience Match",
            "wildcard": "Wildcard Match",
        }.get(self.match_type, self.match_type)

        # Access job seeker through talent sheet
        job_seeker_name = self.talent_sheet.job_seeker.user.get_full_name()
        return f"{job_seeker_name} - {self.job_opening} ({self.match_score}%, {match_type_display})"
