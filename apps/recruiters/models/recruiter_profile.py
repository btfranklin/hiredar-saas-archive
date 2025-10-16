"""Recruiter profile model."""

from __future__ import annotations

from django.db import models

from apps.authentication.models import User


class RecruiterProfile(models.Model):
    """Extended profile for recruiters."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="recruiter_profile",
        limit_choices_to={"user_type": "recruiter"},
    )
    credits_total = models.IntegerField(
        default=100,
        help_text="Total résumé processing credits for the recruiter",
    )
    credits_available = models.IntegerField(
        default=100,
        help_text="Remaining résumé processing credits available",
    )
    total_resumes_processed = models.PositiveIntegerField(
        default=0,
        help_text="Total résumés ever processed",
    )
    total_bulk_uploads_performed = models.PositiveIntegerField(
        default=0,
        help_text="Total bulk résumé uploads performed",
    )
    total_candidates_shortlisted = models.PositiveIntegerField(
        default=0,
        help_text="Total candidates shortlisted",
    )
    total_shortlist_csvs_generated = models.PositiveIntegerField(
        default=0,
        help_text="Total shortlist CSVs generated",
    )
    total_shortlist_pdfs_generated = models.PositiveIntegerField(
        default=0,
        help_text="Total shortlist PDFs generated",
    )

    def __str__(self) -> str:
        return f"Recruiter: {self.user.email}"
