"""
Models for the matching app.

This module defines the models for handling candidate matching.
"""

from decimal import Decimal

from django.db import models

from apps.job_seekers.models import JobSeekerProfile


class CandidateMatch(models.Model):
    """Model for matching job seekers to job openings"""

    job_opening = models.ForeignKey(
        "recruiters.JobOpening",
        on_delete=models.CASCADE,
        related_name="candidate_matches",
    )
    job_seeker = models.ForeignKey(
        JobSeekerProfile,
        on_delete=models.CASCADE,
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
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("withdrawn", "Withdrawn"),
        ),
        default="pending",
    )
    is_shortlisted = models.BooleanField(default=False)
    match_type = models.CharField(
        max_length=20,
        choices=(
            ("top", "Top Match"),
            ("wildcard", "Wildcard Match"),
        ),
        default="top",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "matching"

    def __str__(self) -> str:
        return f"{self.job_seeker} - {self.job_opening} ({self.match_score}%)"
