from typing import Any

from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone

from apps.authentication.models import User


class RecruiterProfile(models.Model):
    """Extended profile for recruiters"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="recruiter_profile",
        limit_choices_to={"user_type": "recruiter"},
    )

    credits_total = models.IntegerField(
        default=100,
        help_text="Total resume processing credits for the recruiter",
    )
    credits_available = models.IntegerField(
        default=100,
        help_text="Remaining resume processing credits available",
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
        help_text="List required skills with experience levels, e.g., 'Python (3+ years) | React (2+ years) | Agile (familiar)'",
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

    def __str__(self) -> str:
        return f"Job Opening: {self.title} ({self.status})"

    @property
    def is_active(self) -> bool:
        """
        Property method for backward compatibility.
        Returns True if status is 'active', False otherwise.
        """
        return self.status == "active"

    @property
    def required_skills_list(self) -> list[str]:
        """Return a list of required skill names"""
        if not self.required_skills:
            return []
        return [
            skill.strip()
            for skill in self.required_skills.split(" | ")
            if skill.strip()
        ]


# --- Bulk Resume Upload -----------------------------------------------------


def default_pool_name() -> str:
    """Generate a default name for a resume pool based on current date/time."""
    return timezone.now().strftime("%Y-%m-%d %H:%M")


class BulkResumeUpload(models.Model):
    """An uploaded named pool of many resumes."""

    name = models.CharField(
        max_length=255,
        default=default_pool_name,
        help_text="Name of this resume pool",
    )
    recruiter = models.ForeignKey(
        RecruiterProfile,
        on_delete=models.CASCADE,
        related_name="bulk_resume_uploads",
    )
    zip_file = models.FileField(
        upload_to="bulk_resumes/zips/",
        help_text="ZIP archive containing PDF resumes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed = models.BooleanField(default=False)
    total_files = models.PositiveIntegerField(default=0)
    processed_files = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Bulk Resume Upload"
        verbose_name_plural = "Bulk Resume Uploads"

    def __str__(self) -> str:  # noqa: D401 – admin friendly string
        return (
            f"ResumePool '{self.name}' – {self.recruiter.user.email} "
            f"({self.processed_files}/{self.total_files})"
        )

    def delete(self, using: str | None = None, keep_parents: bool = False) -> None:
        # Delete the associated ZIP file from storage
        self.zip_file.delete(save=False)
        super().delete(using=using, keep_parents=keep_parents)


class ResumeFile(models.Model):
    """Individual PDF resume extracted from a named pool."""

    bulk_upload = models.ForeignKey(
        BulkResumeUpload,
        on_delete=models.CASCADE,
        related_name="resume_files",
    )
    recruiter = models.ForeignKey(
        RecruiterProfile,
        on_delete=models.CASCADE,
        related_name="resume_files",
    )
    file = models.FileField(upload_to="bulk_resumes/items/")
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Resume File"
        verbose_name_plural = "Resume Files"
        # Ensure a resume file name is unique within a bulk upload
        unique_together = ["bulk_upload", "original_filename"]

    def __str__(self) -> str:  # noqa: D401 – friendly string
        return f"{self.original_filename}"

    def delete(self, using: str | None = None, keep_parents: bool = False) -> None:
        # Delete the associated file from storage
        self.file.delete(save=False)
        super().delete(using=using, keep_parents=keep_parents)


# Ensure file is deleted even when using QuerySet.delete()
@receiver(post_delete, sender=ResumeFile)
def delete_resume_file_file(sender, instance: ResumeFile, **kwargs) -> None:
    # Delete the associated file from storage
    instance.file.delete(save=False)


@receiver(post_delete, sender=BulkResumeUpload)
def delete_bulk_resume_upload_file(
    sender, instance: BulkResumeUpload, **kwargs
) -> None:
    # Delete the associated ZIP file from storage
    instance.zip_file.delete(save=False)
    # Delete any UploadedResumePool created with the same name and recruiter
    from apps.job_seekers.models.profile import UploadedResumePool

    UploadedResumePool.objects.filter(
        recruiter=instance.recruiter.user, name=instance.name
    ).delete()
