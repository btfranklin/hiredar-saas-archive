"""Job opening model."""

from __future__ import annotations

from django.contrib.postgres.indexes import GinIndex
from django.db import models


class JobOpening(models.Model):
    """Job openings posted by recruiters."""

    JOB_LEVEL_CHOICES = (
        ("entry", "Entry Level"),
        ("junior", "Junior"),
        ("mid", "Mid-Level"),
        ("senior", "Senior"),
        ("manager", "Manager"),
        ("executive", "Executive"),
    )

    EMPLOYMENT_TYPE_CHOICES = (
        ("full_time", "Full-time"),
        ("part_time", "Part-time"),
        ("contract", "Contract"),
        ("temporary", "Temporary"),
        ("internship", "Internship"),
    )

    recruiter = models.ForeignKey(
        "recruiters.RecruiterProfile",
        on_delete=models.CASCADE,
        related_name="job_openings",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    original_description = models.TextField(
        blank=True,
        help_text="The original, unmodified job description as provided by the recruiter",
    )
    location = models.CharField(max_length=100, blank=True)
    company = models.CharField(
        max_length=255,
        help_text="Company offering this position",
        default="",
        blank=True,
    )
    job_level = models.CharField(
        max_length=20,
        choices=JOB_LEVEL_CHOICES,
        blank=True,
        help_text="Experience level for the position",
    )
    employment_type = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_TYPE_CHOICES,
        blank=True,
        help_text="Type of employment arrangement",
    )
    salary_min = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    salary_max = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    benefits = models.TextField(
        blank=True,
        help_text="Benefits offered (health insurance, retirement plans, etc.)",
    )
    additional_perks = models.TextField(
        blank=True, help_text="Additional perks (gym membership, food, etc.)"
    )
    required_skills = models.TextField(
        blank=True,
        help_text="List required skills with experience levels, one per line",
    )
    required_qualifications = models.TextField(
        blank=True,
        help_text="Formal education, certifications, or qualifications required",
    )
    experience_required = models.TextField(
        blank=True,
        help_text="Years or type of experience required for this position",
    )
    soft_skills = models.TextField(
        blank=True,
        help_text="Soft skills like communication, leadership, teamwork, etc.",
    )
    responsibilities = models.TextField(
        blank=True, help_text="Comprehensive list of job responsibilities"
    )
    daily_tasks = models.TextField(
        blank=True, help_text="Typical daily, weekly, or monthly tasks for this role"
    )
    performance_expectations = models.TextField(
        blank=True, help_text="Performance targets, quality standards, or deadlines"
    )
    working_hours = models.CharField(
        max_length=100,
        blank=True,
        help_text="Working hours schedule (e.g., '9-5, M-F')",
    )
    work_environment = models.CharField(
        max_length=100,
        blank=True,
        help_text="Work environment (office, remote, hybrid, etc.)",
    )
    reporting_to = models.CharField(
        max_length=100, blank=True, help_text="Position or title this role reports to"
    )
    travel_requirements = models.CharField(
        max_length=100,
        blank=True,
        help_text="Travel expectations (e.g., '25% travel' or 'occasional travel required')",
    )
    status = models.CharField(
        max_length=20,
        choices=(
            ("active", "Active"),
            ("draft", "Draft"),
            ("closed", "Closed"),
        ),
        default="draft",
        help_text="Current status of the job opening",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    candidate_pool_id = models.PositiveIntegerField(
        default=0,
        help_text="Candidate pool to match against (0 = global talent pool)",
    )

    def __str__(self) -> str:
        return f"Job Opening: {self.title} ({self.status})"

    @property
    def is_active(self) -> bool:
        return self.status == "active"

    @property
    def required_skills_list(self) -> list[str]:
        if not self.required_skills:
            return []
        return [
            skill.strip()
            for skill in self.required_skills.splitlines()
            if skill.strip()
        ]

    class Meta:
        indexes = [
            GinIndex(
                name="jobopening_title_trgm",
                fields=["title"],
                opclasses=["gin_trgm_ops"],
            ),
            GinIndex(
                name="jobopening_requiredskills_trgm",
                fields=["required_skills"],
                opclasses=["gin_trgm_ops"],
            ),
        ]
