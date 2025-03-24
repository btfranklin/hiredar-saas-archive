from typing import Any

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
    subscription_tier = models.CharField(
        max_length=20,
        choices=(
            ("free", "Free"),
            ("premium", "Premium"),
        ),
        default="free",
    )

    def __str__(self) -> str:
        return f"Recruiter: {self.user.email}"


class JobOpeningProcessingTask(models.Model):
    """
    Model for tracking progress of job opening description processing.

    This tracks the progress of a job description being processed by the LLM
    and converted to a structured JobOpening instance.
    """

    # Processing status choices
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    )

    # Task identification
    task_id = models.CharField(max_length=100, primary_key=True)
    recruiter = models.ForeignKey(
        RecruiterProfile,
        on_delete=models.CASCADE,
        related_name="job_processing_tasks",
    )

    # Processing metadata
    job_title = models.CharField(max_length=255)
    original_text = models.TextField()
    processed_xml = models.TextField(blank=True, null=True)
    created_job_opening_id = models.IntegerField(blank=True, null=True)

    # Processing status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    progress_percent = models.IntegerField(default=0)
    current_step = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def update_progress(self, step: str, progress: int, message: str = "") -> None:
        """
        Update the progress of this processing task.

        Args:
            step: Current processing step
            progress: Progress percentage (0-100)
            message: Optional status message
        """
        self.current_step = step
        self.progress_percent = progress
        if message:
            self.message = message
        self.save(
            update_fields=["current_step", "progress_percent", "message", "updated_at"]
        )

    def mark_completed(self, job_opening_id: int, processed_xml: str) -> None:
        """
        Mark this task as completed.

        Args:
            job_opening_id: ID of the created JobOpening
            processed_xml: The processed XML representation of the job
        """
        self.status = "completed"
        self.progress_percent = 100
        self.created_job_opening_id = job_opening_id
        self.processed_xml = processed_xml
        self.message = "Job opening created successfully."
        self.save()

    def mark_failed(self, message: str) -> None:
        """
        Mark this task as failed.

        Args:
            message: Error message explaining the failure
        """
        self.status = "failed"
        self.message = message
        self.save()

    def to_dict(self) -> dict[str, Any]:
        """
        Convert task progress to a dictionary for API responses.

        Returns:
            Dictionary with task progress information
        """
        return {
            "task_id": self.task_id,
            "status": self.status,
            "progress_percent": self.progress_percent,
            "current_step": self.current_step,
            "message": self.message,
            "created_job_opening_id": self.created_job_opening_id,
            "job_title": self.job_title,
        }

    def __str__(self) -> str:
        return f"Job Processing Task: {self.job_title} ({self.status})"


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
