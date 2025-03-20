from django.db import models

from apps.authentication.models import User


class RecruiterProfile(models.Model):
    """Extended profile for recruiters"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="recruiter_profile",
        limit_choices_to={"user_type": "recruiter"},
    )

    # Subscription status
    is_subscribed = models.BooleanField(default=False)
    subscription_tier = models.CharField(
        max_length=20,
        choices=(
            ("basic", "Basic"),
            ("professional", "Professional"),
            ("enterprise", "Enterprise"),
        ),
        default="basic",
    )

    def __str__(self) -> str:
        return f"Recruiter: {self.user.email}"


class JobOpening(models.Model):
    """Model for job openings posted by recruiters"""

    # Job Classification Choices
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

    # Basic Information
    recruiter = models.ForeignKey(
        RecruiterProfile,
        on_delete=models.CASCADE,
        related_name="job_openings",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=100, blank=True)
    company = models.CharField(
        max_length=255,
        help_text="Company offering this position",
        default="",
        blank=True,
    )

    # Job Classification
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

    # Compensation & Benefits
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

    # Qualifications & Skills
    required_skills = models.TextField(
        blank=True,
        help_text="List required skills with experience levels, e.g., 'Python (3+ years), React (2+ years), Agile (familiar)'",
    )
    required_qualifications = models.TextField(
        blank=True,
        help_text="Formal education, certifications, or qualifications required",
    )
    soft_skills = models.TextField(
        blank=True,
        help_text="Soft skills like communication, leadership, teamwork, etc.",
    )

    # Job Details
    responsibilities = models.TextField(
        blank=True, help_text="Comprehensive list of job responsibilities"
    )
    daily_tasks = models.TextField(
        blank=True, help_text="Typical daily, weekly, or monthly tasks for this role"
    )
    performance_expectations = models.TextField(
        blank=True, help_text="Performance targets, quality standards, or deadlines"
    )

    # Working Conditions
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

    # Metadata
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
