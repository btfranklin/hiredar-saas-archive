import json
from datetime import timedelta
from typing import Any

from django.db import models
from django.utils import timezone

from apps.authentication.models import User


class ResumeProcessingTaskProgress(models.Model):
    """Model to track progress of resume processing tasks"""

    class Meta:
        db_table = "resume_processing_resumeprocessingtaskprogress"
        verbose_name = "Resume Processing Task Progress"
        verbose_name_plural = "Resume Processing Task Progress"

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
    RESUME_PROCESSING_STEPS: list[dict[str, Any]] = [
        {
            "id": "file_path_resolved",
            "name": "Preparing File",
            "description": "Locating and preparing the résumé file",
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
            "name": "Analyzing Résumé",
            "description": "Analyzing résumé with AI to extract structured data",
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
        cutoff_date = timezone.now() - timedelta(days=days)
        return cls.objects.filter(created_at__lt=cutoff_date).delete()[0]

    @classmethod
    def clean_up_completed_records(cls, minutes: int = 5) -> int:
        cutoff_time = timezone.now() - timedelta(minutes=minutes)
        return cls.objects.filter(
            status__in=["completed", "failed"], updated_at__lt=cutoff_time
        ).delete()[0]

    @property
    def completed_steps(self) -> list[str]:
        try:
            return json.loads(self.steps_completed)
        except json.JSONDecodeError:
            return []

    def mark_step_complete(self, step_id: str) -> None:
        completed = self.completed_steps
        if step_id not in completed:
            completed.append(step_id)
            self.steps_completed = json.dumps(completed)
            self._update_current_step(step_id)
            self._calculate_progress()
            self.save(
                update_fields=["steps_completed", "current_step", "progress_percent"]
            )

    def _update_current_step(self, completed_step: str) -> None:
        step_ids = [step["id"] for step in self.RESUME_PROCESSING_STEPS]
        try:
            idx = step_ids.index(completed_step)
            if idx < len(step_ids) - 1:
                self.current_step = step_ids[idx + 1]
            else:
                self.status = "completed"
                self.message = "Résumé processing completed successfully"
        except ValueError:
            pass

    def _calculate_progress(self) -> None:
        completed = self.completed_steps
        weights = {step["id"]: step["weight"] for step in self.RESUME_PROCESSING_STEPS}
        total_weight = sum(step["weight"] for step in self.RESUME_PROCESSING_STEPS)
        completed_weight = sum(weights.get(sid, 0) for sid in completed)
        self.progress_percent = (
            int((completed_weight / total_weight) * 100) if total_weight else 0
        )

    def __str__(self) -> str:  # noqa: D401 – human readable identifier
        """Return a concise representation suitable for admin lists."""

        return (
            f"TaskProgress {self.task_id} – {self.user.email} ({self.status}, "
            f"{self.progress_percent}%)"
        )

    def to_dict(self) -> dict[str, Any]:
        all_steps = {step["id"]: step for step in self.RESUME_PROCESSING_STEPS}
        completed_ids = self.completed_steps
        detailed = [
            {
                "id": step["id"],
                "name": step["name"],
                "description": step["description"],
                "completed": (step["id"] in completed_ids),
                "current": (step["id"] == self.current_step),
            }
            for step in self.RESUME_PROCESSING_STEPS
        ]
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
            "steps": detailed,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
