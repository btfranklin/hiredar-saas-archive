"""Job opening processing task model."""

from __future__ import annotations

from typing import Any

from django.db import models


class JobOpeningProcessingTask(models.Model):
    """Track progress of job opening description processing."""

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    )

    task_id = models.CharField(max_length=100, primary_key=True)
    recruiter = models.ForeignKey(
        "recruiters.RecruiterProfile",
        on_delete=models.CASCADE,
        related_name="job_processing_tasks",
    )
    job_title = models.CharField(max_length=255)
    original_text = models.TextField()
    processed_xml = models.TextField(blank=True, null=True)
    created_job_opening_id = models.IntegerField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    progress_percent = models.IntegerField(default=0)
    current_step = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def update_progress(self, step: str, progress: int, message: str = "") -> None:
        self.current_step = step
        self.progress_percent = progress
        if message:
            self.message = message
        self.save(
            update_fields=["current_step", "progress_percent", "message", "updated_at"]
        )

    def mark_completed(self, job_opening_id: int, processed_xml: str) -> None:
        self.status = "completed"
        self.progress_percent = 100
        self.created_job_opening_id = job_opening_id
        self.processed_xml = processed_xml
        self.message = "Job opening created successfully."
        self.save()

    def mark_failed(self, message: str) -> None:
        self.status = "failed"
        self.message = message
        self.save()

    def to_dict(self) -> dict[str, Any]:
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
