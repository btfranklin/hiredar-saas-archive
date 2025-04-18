import json
from datetime import timedelta
from typing import Any

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from apps.authentication.models import User


class UploadedResumePool(models.Model):
    """
    Represents a batch of resumes uploaded by a recruiter for a specific job opening.
    """

    recruiter = models.ForeignKey(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="uploaded_resume_pools",
        limit_choices_to={"user_type": "recruiter"},
    )
    job_opening = models.ForeignKey(
        "recruiters.JobOpening",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_resume_pools",
        help_text="Job opening associated with this pool (optional, non-ownership)",
    )
    name = models.CharField(
        max_length=255, help_text='Label for this pool (e.g. "March 2024 Upload")'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Resume Pool: {self.name} ({self.recruiter.email})"


class JobSeekerProfile(models.Model):
    """Extended profile for job seekers (now supports polymorphic owner)"""

    # Polymorphic owner: can be User or UploadedResumePool
    owner_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    owner_object_id = models.PositiveIntegerField(null=True, blank=True)
    owner = GenericForeignKey("owner_content_type", "owner_object_id")

    skills = models.TextField(blank=True, help_text="Pipe-separated list of skills")
    experience = models.TextField(null=True, blank=True)
    education = models.TextField(null=True, blank=True)
    certifications = models.TextField(null=True, blank=True)
    years_of_experience = models.PositiveIntegerField(null=True, blank=True)
    desired_role = models.CharField(max_length=100, null=True, blank=True)
    most_recent_title = models.CharField(max_length=100, null=True, blank=True)
    professional_summary = models.TextField(
        null=True,
        blank=True,
        help_text="Professional summary highlighting experience and qualifications",
    )
    personal_tagline = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        help_text="AI-generated personal identity tagline",
    )
    resume_xml = models.TextField(
        null=True, blank=True, help_text="XML representation of the parsed resume"
    )
    phone = models.CharField(
        max_length=20, null=True, blank=True, help_text="Phone number"
    )
    location = models.CharField(
        max_length=100, blank=True, help_text="Job seeker's location"
    )

    # Social links
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)

    def __str__(self) -> str:
        if self.user_owner:
            return f"Job Seeker: {self.user_owner.email}"
        if self.uploaded_resume_pool:
            return f"Job Seeker (Pool: {self.uploaded_resume_pool.name})"
        return f"Job SeekerProfile {self.pk}"

    @property
    def uploaded_resume_pool(self) -> UploadedResumePool | None:
        if isinstance(self.owner, UploadedResumePool):
            return self.owner
        return None

    @property
    def user_owner(self) -> User | None:
        if isinstance(self.owner, User):
            return self.owner
        return None

    @property
    def skills_list(self) -> list[str]:
        """
        Returns a list of skill names from the pipe-separated skills field.

        Returns:
            list[str]: A list of skill names.
        """
        if not self.skills:
            return []
        return [skill.strip() for skill in self.skills.split("|") if skill.strip()]

    @property
    def in_talent_pool(self) -> bool:
        """
        Determines if the job seeker is in the talent pool.

        A job seeker is in the talent pool if they have a published talent sheet.

        Returns:
            bool: True if the job seeker is in the talent pool, False otherwise.
        """
        # Prevent circular imports by importing here
        from apps.job_seekers.models import TalentSheet

        try:
            # Check if there's a published talent sheet for this job seeker
            return TalentSheet.objects.filter(
                job_seeker=self, is_published=True
            ).exists()
        except Exception:
            return False


class ResumeProcessingTaskProgress(models.Model):
    """Model to track progress of resume processing tasks"""

    # Task identification
    task_id = models.CharField(
        max_length=50, primary_key=True, help_text="Django Q2 task ID"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="resume_processing_progress"
    )
    task_type = models.CharField(
        max_length=50,
        default="resume_processing",
        help_text="Type of task being processed",
    )

    # Progress tracking
    current_step = models.CharField(
        max_length=100, default="initializing", help_text="Current step being processed"
    )
    progress_percent = models.IntegerField(
        default=0, help_text="Overall progress percentage (0-100)"
    )
    steps_completed = models.TextField(
        blank=True, default="[]", help_text="JSON list of completed steps"
    )

    # Status fields
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("running", "Running"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="pending",
    )
    message = models.TextField(blank=True, help_text="Status message or error details")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Define step details as class constants
    RESUME_PROCESSING_STEPS = [
        {
            "id": "file_path_resolved",
            "name": "Preparing File",
            "description": "Locating and preparing the resume file",
            "weight": 5,
        },
        {
            "id": "text_extracted",
            "name": "Extracting Text",
            "description": "Converting PDF to readable text",
            "weight": 15,
        },
        {
            "id": "xml_generated",
            "name": "Analyzing Resume",
            "description": "Analyzing resume with AI to extract structured data",
            "weight": 35,
        },
        {
            "id": "xml_parsed",
            "name": "Processing Data",
            "description": "Processing and organizing the extracted information",
            "weight": 20,
        },
        {
            "id": "profile_updated",
            "name": "Updating Profile",
            "description": "Updating your profile with the extracted information",
            "weight": 15,
        },
        {
            "id": "personal_tagline_generated",
            "name": "Generating Tagline",
            "description": "Creating your personal identity tagline",
            "weight": 5,
        },
        {
            "id": "temp_file_deleted",
            "name": "Cleaning Up",
            "description": "Finalizing profile creation and cleaning up temporary files",
            "weight": 5,
        },
    ]

    @classmethod
    def clean_up_old_records(cls, days: int = 7) -> int:
        """
        Clean up old ResumeProcessingTaskProgress records.

        Args:
            days: Number of days to keep records (default: 7)

        Returns:
            Number of records deleted
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        return cls.objects.filter(created_at__lt=cutoff_date).delete()[0]

    @classmethod
    def clean_up_completed_records(cls, minutes: int = 5) -> int:
        """
        Clean up completed/failed ResumeProcessingTaskProgress records that are older than specified minutes.

        This is useful for removing records that have already been seen by the UI.

        Args:
            minutes: Number of minutes to keep completed records (default: 5)

        Returns:
            Number of records deleted
        """
        cutoff_time = timezone.now() - timedelta(minutes=minutes)
        return cls.objects.filter(
            status__in=["completed", "failed"], updated_at__lt=cutoff_time
        ).delete()[0]

    @property
    def completed_steps(self) -> list[str]:
        """Get list of completed step IDs"""
        try:
            return json.loads(self.steps_completed)
        except json.JSONDecodeError:
            return []

    def mark_step_complete(self, step_id: str) -> None:
        """Mark a specific step as complete and update progress"""
        completed = self.completed_steps

        # Add step if not already completed
        if step_id not in completed:
            completed.append(step_id)
            self.steps_completed = json.dumps(completed)

            # Update current step to the next step
            self._update_current_step(step_id)

            # Calculate progress percentage based on completed steps
            self._calculate_progress()

            self.save(
                update_fields=["steps_completed", "current_step", "progress_percent"]
            )

    def _update_current_step(self, completed_step: str) -> None:
        """Update current step to the next step after the one just completed"""
        step_ids = [step["id"] for step in self.RESUME_PROCESSING_STEPS]

        try:
            current_index = step_ids.index(completed_step)
            if current_index < len(step_ids) - 1:
                self.current_step = step_ids[current_index + 1]
            else:
                # Last step completed
                self.status = "completed"
                self.message = "Resume processing completed successfully"
        except ValueError:
            # Step not found in the list
            pass

    def _calculate_progress(self) -> None:
        """Calculate progress percentage based on completed steps and their weights"""
        completed = self.completed_steps

        # Create a mapping of step IDs to their weights
        weights = {step["id"]: step["weight"] for step in self.RESUME_PROCESSING_STEPS}

        # Calculate total weight of all steps
        total_weight = sum(step["weight"] for step in self.RESUME_PROCESSING_STEPS)

        # Calculate completed weight
        completed_weight = sum(weights.get(step_id, 0) for step_id in completed)

        # Calculate progress percentage
        if total_weight > 0:
            self.progress_percent = int((completed_weight / total_weight) * 100)
        else:
            self.progress_percent = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert ResumeProcessingTaskProgress to a dictionary for API responses"""
        # Get step details
        all_steps = {step["id"]: step for step in self.RESUME_PROCESSING_STEPS}

        # Process completed and remaining steps
        completed_step_ids = self.completed_steps
        detailed_steps = []

        for step in self.RESUME_PROCESSING_STEPS:
            step_id = step["id"]
            detailed_steps.append(
                {
                    "id": step_id,
                    "name": step["name"],
                    "description": step["description"],
                    "completed": step_id in completed_step_ids,
                    "current": step_id == self.current_step,
                }
            )

        return {
            "task_id": self.task_id,
            "status": self.status,
            "message": self.message,
            "progress_percent": self.progress_percent,
            "current_step": self.current_step,
            "current_step_name": all_steps.get(self.current_step, {}).get("name", ""),
            "current_step_description": all_steps.get(self.current_step, {}).get(
                "description", ""
            ),
            "steps": detailed_steps,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RoleRecommendation(models.Model):
    """
    Stores AI-generated role recommendations for job seekers based on their skills and experience.

    These recommendations are created by analyzing the job seeker's resume (XML) data
    using AI to identify potential next career opportunities that align with their
    background, skills, and industry expertise. Each recommendation represents a real
    role that would be a logical next position in the job seeker's career progression.
    """

    job_seeker = models.ForeignKey(
        "job_seekers.JobSeekerProfile",
        on_delete=models.CASCADE,
        related_name="role_recommendations",
        help_text="The job seeker this role recommendation is for",
    )
    role_title = models.CharField(
        max_length=100,
        help_text="The title of the recommended role, in title case (e.g., 'Senior Software Engineer')",
    )
    description = models.TextField(
        help_text="A concise description of the role, outlining key responsibilities and value proposition",
    )
    is_candidate_interested = models.BooleanField(
        default=False,
        help_text="Indicates whether the job seeker has expressed interest in this role",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this recommendation was generated",
    )

    def __str__(self) -> str:
        # Use user_owner if available, otherwise just use the job_seeker pk
        user_name = (
            self.job_seeker.user_owner.name
            if self.job_seeker.user_owner
            else f"Profile {self.job_seeker.pk}"
        )
        return f"{self.role_title} for {user_name}"

    @property
    def uploaded_resume_pool(self) -> UploadedResumePool | None:
        """Access the resume pool through the job_seeker relationship."""
        return self.job_seeker.uploaded_resume_pool if self.job_seeker else None

    class Meta:
        ordering = ["role_title"]


class TalentSheet(models.Model):
    """
    AI-generated talent sheet for job seekers in the talent pool.

    This represents a comprehensive, recruiter-friendly presentation of a job seeker's
    qualifications, tailored for the talent pool. Generated when a job seeker opts
    into the talent pool, this sheet provides a structured presentation of their
    skills, experience, and career goals that makes it easier for recruiters to
    quickly assess their suitability for open positions.
    """

    job_seeker = models.OneToOneField(
        "job_seekers.JobSeekerProfile",
        on_delete=models.CASCADE,
        related_name="talent_sheet",
        help_text="The job seeker this talent sheet is for",
    )
    promotional_blurb = models.TextField(
        help_text="AI-generated promotional summary highlighting the candidate's unique value proposition"
    )
    skill_overview = models.TextField(
        help_text="Concise overview of the candidate's key skills and competencies"
    )
    ideal_roles = models.TextField(
        blank=True,
        help_text="Comma-separated list of ideal roles, populated from their interested role recommendations",
    )
    personal_tagline = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        help_text="AI-generated personal identity tagline",
    )
    salary_min = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum salary expectation",
    )
    is_published = models.BooleanField(
        default=False,
        help_text="Whether this talent sheet is published and available for matching to job openings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        # Use user_owner if available, otherwise just use the job_seeker pk
        user_name = (
            self.job_seeker.user_owner.name
            if self.job_seeker.user_owner
            else f"Profile {self.job_seeker.pk}"
        )
        return f"Talent Sheet: {user_name}"

    @property
    def uploaded_resume_pool(self) -> UploadedResumePool | None:
        """Access the resume pool through the job_seeker relationship."""
        return self.job_seeker.uploaded_resume_pool if self.job_seeker else None

    @property
    def ideal_roles_list(self) -> list[str]:
        """Returns a list of ideal roles from the comma-separated string"""
        if not self.ideal_roles:
            return []
        return [role.strip() for role in self.ideal_roles.split(",")]
