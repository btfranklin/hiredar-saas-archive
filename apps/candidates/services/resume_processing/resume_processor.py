"""Resume processing service.

Canonical helper layer for creating/tracking resume‑processing tasks,
updating profiles from extracted data, and handling recruiter ZIP batch
uploads.
"""

from __future__ import annotations

from typing import Any

# Celery result backend
from celery.result import AsyncResult

from apps.authentication.models import User
from apps.core.tasks import safe_async_task
from apps.candidates.models import ResumeProcessingTaskProgress

__all__ = [
    "ResumeProcessor",
]

async_task = safe_async_task


class _DummyTaskProgress:  # noqa: D401 – internal helper
    """Synthetic task‑progress instance when only a Django‑Q result exists."""

    def __init__(self, task_id: str, result_data: dict):
        self.task_id = task_id
        # Map Django‑Q *success* → completed/failed for UI parity
        self.status = (
            "completed" if result_data.get("status", "error") == "success" else "failed"
        )
        self.message = result_data.get("message", "")
        self._result_data = result_data

    # A minimal POJO so the view layer can render the progress widget
    def to_dict(self) -> dict:
        return {
            "progress_percent": 100 if self.status == "completed" else 0,
            "current_step": self.status,
            "current_step_name": "Complete" if self.status == "completed" else "Failed",
            "steps": [],
        }


class ResumeProcessor:  # noqa: D401 – Service class, not data‑class
    """Helper service for creating and tracking resume‑processing tasks."""

    # ---------------------------------------------------------------------
    # Task‑tracking helpers
    # ---------------------------------------------------------------------
    @staticmethod
    def create_processing_task(user: User, task_id: str):
        """Persist a *pending* ResumeProcessingTaskProgress row."""
        return ResumeProcessingTaskProgress.objects.create(
            task_id=task_id,
            user=user,
            task_type="resume_processing",
            status="pending",
            message="Preparing to process résumé",
            current_step="file_path_resolved",
            progress_percent=0,
        )

    @staticmethod
    def get_task_status(task_id: str, user: User | None = None):
        """Return the DB progress row *or* fallback to a Django‑Q result."""
        try:
            qry: dict[str, Any] = {"task_id": task_id}
            if user is not None:
                qry["user"] = user
            return ResumeProcessingTaskProgress.objects.get(**qry)
        except ResumeProcessingTaskProgress.DoesNotExist:
            pass

        # Fallback → Django‑Q result (may be expired though)
        # Fallback → Celery result (if DB record not found)
        async_result = AsyncResult(task_id)
        # Map Celery statuses to our simplified status values
        if async_result.successful():
            status = "completed"
        elif async_result.failed():
            status = "failed"
        elif async_result.status == "STARTED":
            status = "running"
        else:
            status = "pending"
        # Capture failure message if any
        message = None
        if async_result.status == "FAILURE":
            message = str(async_result.result)

        # Synthetic progress object for Celery tasks
        class _CeleryTaskProgress:
            def __init__(self, task_id: str, status: str, message: str | None):
                self.task_id = task_id
                self.status = status
                self.message = message or ""

            def to_dict(self) -> dict[str, Any]:
                return {
                    "task_id": self.task_id,
                    "status": self.status,
                    "message": self.message,
                    "progress_percent": 100 if self.status == "completed" else 0,
                    "current_step": self.status,
                    "current_step_name": "Complete" if self.status == "completed" else self.status.capitalize(),
                    "steps": [],
                }

        return _CeleryTaskProgress(task_id, status, message)

    @staticmethod
    def update_task_progress(task_id: str, step_id: str, message: str | None = None):
        task = ResumeProcessingTaskProgress.objects.get(task_id=task_id)
        task.mark_step_complete(step_id)
        if message:
            task.message = message
            task.save(update_fields=["message"])
        return task

    @staticmethod
    def fail_task(task_id: str, error_message: str):
        task = ResumeProcessingTaskProgress.objects.get(task_id=task_id)
        task.status = "failed"
        task.message = error_message
        task.save(update_fields=["status", "message"])
        return task
