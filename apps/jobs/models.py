from decimal import Decimal

from django.db import models

from apps.job_seekers.models import JobSeekerProfile
from apps.recruiters.models import RecruiterProfile


class JobOpening(models.Model):
    """Model for job openings posted by recruiters"""

    recruiter = models.ForeignKey(
        RecruiterProfile,
        on_delete=models.CASCADE,
        related_name="job_openings",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=100)
    company = models.CharField(
        max_length=255, help_text="Company offering this position", default=""
    )
    salary_min = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    salary_max = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    required_skills = models.TextField(
        blank=True, help_text="Comma-separated list of required skills"
    )
    experience_years = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.title} - {self.company}"

    @property
    def required_skills_list(self) -> list[str]:
        """Return a list of required skill names"""
        if not self.required_skills:
            return []
        return [
            skill.strip() for skill in self.required_skills.split(",") if skill.strip()
        ]


class CandidateMatch(models.Model):
    """Model for matching job seekers to job openings"""

    job_opening = models.ForeignKey(
        JobOpening,
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

    def __str__(self) -> str:
        return f"{self.job_seeker} - {self.job_opening} ({self.match_score}%)"
