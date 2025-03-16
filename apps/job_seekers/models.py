import json
from datetime import timedelta
from typing import Any

from django.db import models
from django.utils import timezone

from apps.authentication.models import User


class JobSeekerProfile(models.Model):
    """Extended profile for job seekers"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="job_seeker_profile",
        limit_choices_to={"user_type": "job_seeker"},
    )
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

    # Social links
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)

    def __str__(self) -> str:
        return f"Job Seeker: {self.user.email}"

    @property
    def skills_list(self) -> list[str]:
        """Return a list of skill names"""
        if not self.skills:
            return []
        return [skill.strip() for skill in self.skills.split(" | ") if skill.strip()]


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
            "weight": 40,
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
    Stores role recommendations for job seekers based on their skills and experience.

    These recommendations are generated using AI matching algorithms that analyze
    the job seeker's profile, skills, and experience to suggest relevant roles.
    """

    job_seeker = models.ForeignKey(
        "job_seekers.JobSeekerProfile",
        on_delete=models.CASCADE,
        related_name="role_recommendations",
    )
    role_title = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.job_seeker} - {self.role_title}"

    class Meta:
        ordering = ["role_title"]
