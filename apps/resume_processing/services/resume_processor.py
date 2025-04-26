"""Resume processing service.

Canonical helper layer for creating/tracking resume‑processing tasks,
updating profiles from extracted data, and handling recruiter ZIP batch
uploads.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from typing import Any
from zipfile import ZipFile

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django_q.tasks import result

from apps.authentication.models import User
from apps.core.tasks import safe_async_task
from apps.job_seekers.models.profile import UploadedResumePool
from apps.job_seekers.services.profile_manager import ProfileManager
from apps.job_seekers.tasks.pool_tasks import (
    cleanup_temp_resume_file,
    process_resume_for_pool,
)
from apps.recruiters.models import JobOpening
from apps.resume_processing.models import ResumeProcessingTaskProgress

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
            message="Preparing to process resume",
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
        task_result = result(task_id)
        return (
            _DummyTaskProgress(task_id, task_result)
            if task_result is not None
            else None
        )

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

    # ------------------------------------------------------------------
    # Profile helpers
    # ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def update_profile_from_resume_data(user: User, resume_data: dict):
        profile = ProfileManager.get_profile(
            user
        ) or ProfileManager.create_or_update_profile(user, {})

        field_mapping = {
            "skills": "skills",
            "experience": "experience",
            "education": "education",
            "certifications": "certifications",
            "years_of_experience": "years_of_experience",
            "current_title": "most_recent_title",
            "summary": "professional_summary",
            "phone": "phone",
            "location": "location",
            "resume_xml": "resume_xml",
        }

        for resume_field, profile_field in field_mapping.items():
            value = resume_data.get(resume_field)
            if not value:
                continue
            if resume_field == "skills" and isinstance(value, list):
                value = " | ".join(skill.strip() for skill in value if skill.strip())
            setattr(profile, profile_field, value)

        profile.save()
        return profile

    # ------------------------------------------------------------------
    # Bulk‑ZIP helper – used by recruiters uploading pools of résumés
    # ------------------------------------------------------------------
    @staticmethod
    def process_resume_batch_from_zip(
        recruiter: User,
        zip_file: UploadedFile,
        pool_name: str,
        job_opening_id: int | None = None,
    ) -> tuple[UploadedResumePool, list[str]]:
        # 1. Create a pool row so we can attach profiles later
        pool = UploadedResumePool.objects.create(recruiter=recruiter, name=pool_name)

        if job_opening_id:
            try:
                pool.job_opening = JobOpening.objects.get(pk=job_opening_id)
                pool.save()
            except JobOpening.DoesNotExist:
                print(f"Warning: Job opening with ID {job_opening_id} not found.")

        temp_dir = tempfile.mkdtemp(prefix="resume_batch_")
        task_ids: list[str] = []

        try:
            with ZipFile(zip_file, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            for root, _, files in os.walk(temp_dir):
                for filename in files:
                    if not filename.lower().endswith(".pdf"):
                        continue
                    file_path = os.path.join(root, filename)
                    task_id = str(uuid.uuid4())

                    # Process each resume via the job_seekers pool pipeline
                    async_task(
                        process_resume_for_pool,
                        file_path,
                        pool.pk,
                        task_id,
                        hook=cleanup_temp_resume_file,
                    )
                    task_ids.append(task_id)
        except Exception as exc:  # noqa: BLE001 – keep broad to ensure cleanup
            print(f"Error processing ZIP file: {exc}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return pool, []

        return pool, task_ids
