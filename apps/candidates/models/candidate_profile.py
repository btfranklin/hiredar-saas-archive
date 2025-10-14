"""Candidate profile model blending resume data and presentation fields."""

from __future__ import annotations

from django.contrib.postgres.indexes import GinIndex
from django.db import models


class CandidateProfile(models.Model):
    """
    Normalised candidate representation owned by a recruiter.

    This model combines structured resume data with the AI-generated
    presentation content so downstream systems can work with a single
    source of truth.
    """

    pool = models.ForeignKey(
        "candidates.CandidatePool",
        on_delete=models.CASCADE,
        related_name="candidate_profiles",
        help_text="Candidate pool that owns this candidate record",
    )
    candidate_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Full name parsed from the resume or provided by a recruiter",
    )
    most_recent_title = models.CharField(
        max_length=150,
        blank=True,
        help_text="Most recent job title extracted from the resume",
    )
    desired_role = models.CharField(
        max_length=150,
        blank=True,
        help_text="Role or career direction the candidate is interested in",
    )
    years_of_experience = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total years of professional experience",
    )
    location = models.CharField(
        max_length=100,
        blank=True,
        help_text="Candidate location or preferred working location",
    )
    phone = models.CharField(
        max_length=30,
        blank=True,
        help_text="Phone number if provided in the resume",
    )
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)

    resume_xml = models.TextField(
        blank=True,
        help_text="Structured XML representation of the candidate resume",
    )

    skills = models.TextField(
        blank=True,
        help_text="Line-separated list of skills extracted from the resume",
    )
    experience = models.TextField(
        blank=True,
        help_text="Detailed experience content extracted from the resume",
    )
    education = models.TextField(
        blank=True,
        help_text="Education history extracted from the resume",
    )
    certifications = models.TextField(
        blank=True,
        help_text="Certifications extracted from the resume",
    )
    professional_summary = models.TextField(
        blank=True,
        help_text="Structured summary of professional accomplishments",
    )

    personal_tagline = models.CharField(
        max_length=150,
        blank=True,
        help_text="Short AI-generated tagline introducing the candidate",
    )
    promotional_blurb = models.TextField(
        blank=True,
        help_text="AI-generated promotional overview for recruiter-facing views",
    )
    experience_overview = models.TextField(
        blank=True,
        help_text="High-level narrative of the candidate's experience",
    )
    ideal_roles = models.TextField(
        blank=True,
        help_text="Comma-separated list of ideal roles generated from recommendations",
    )
    qualifications = models.TextField(
        blank=True,
        help_text="Combined education and certifications summary for matching",
    )
    salary_min = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum salary expectation if available",
    )
    is_published = models.BooleanField(
        default=False,
        help_text="Whether this profile is eligible for matching workflows",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            GinIndex(
                name="candidateprofile_skills_trgm",
                fields=["skills"],
                opclasses=["gin_trgm_ops"],
            ),
        ]
        ordering = ("-created_at",)

    def __str__(self) -> str:
        name = self.candidate_name or self.most_recent_title or f"Candidate {self.pk}"
        return f"{name} ({self.pool.name})"

    @property
    def skills_list(self) -> list[str]:
        """Return skills as a cleaned list."""
        if not self.skills:
            return []
        return [skill.strip() for skill in self.skills.splitlines() if skill.strip()]

    @property
    def ideal_roles_list(self) -> list[str]:
        """Return ideal roles as a cleaned list."""
        if not self.ideal_roles:
            return []
        return [role.strip() for role in self.ideal_roles.split(",") if role.strip()]
