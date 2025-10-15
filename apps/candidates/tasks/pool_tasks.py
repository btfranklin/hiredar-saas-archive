"""Tasks for processing resumes uploaded into a candidate pool."""

from __future__ import annotations

import os
from typing import Any

from celery import shared_task
from django.db.models import F

from apps.candidates.models import CandidatePool, CandidateProfile
from apps.candidates.tasks.profile_enrichment_tasks import (
    generate_profile_enrichment_task,
)
from apps.core.models import TaskMeta
from apps.core.tasks import safe_async_task
from apps.recruiters.models import BulkResumeUpload, RecruiterProfile

from .personal_tagline_tasks import generate_personal_tagline

async_task = safe_async_task


@shared_task(name="apps.candidates.tasks.pool_tasks.process_resume_for_pool")
def process_resume_for_pool(
    file_path: str,
    pool_id: int,
    bulk_pk: int,
    meta_pk: str | None = None,
) -> dict[str, Any]:
    """
    Process an uploaded resume and create a CandidateProfile in the specified pool.
    """
    try:
        candidate_pool = CandidatePool.objects.get(pk=pool_id)
        bulk = BulkResumeUpload.objects.select_related("recruiter").get(pk=bulk_pk)
    except CandidatePool.DoesNotExist:
        return {
            "status": "error",
            "message": f"Candidate pool with ID {pool_id} not found",
            "file_path": file_path,
        }

    temp_profile = CandidateProfile(pool=candidate_pool)
    temp_profile.save()

    try:
        from apps.candidates.services.resume_pipeline import process_resume

        result = process_resume(file_path, temp_profile, None)

        if not result.get("success", False):
            temp_profile.delete()
            BulkResumeUpload.objects.filter(pk=bulk_pk).update(
                processed_profiles=F("processed_profiles") + 1
            )
            RecruiterProfile.objects.filter(pk=bulk.recruiter.pk).update(
                total_resumes_processed=F("total_resumes_processed") + 1
            )
            return {
                "status": "error",
                "message": result.get("message", "Failed to process resume"),
                "file_path": file_path,
            }

        resume_data = result.get("profile_data", {}) or {}
        personal = resume_data.get("personal_details", {}) or {}
        has_minimum_data = bool(personal.get("name")) or bool(resume_data.get("skills"))

        if not has_minimum_data:
            temp_profile.delete()
            BulkResumeUpload.objects.filter(pk=bulk_pk).update(
                processed_profiles=F("processed_profiles") + 1
            )
            RecruiterProfile.objects.filter(pk=bulk.recruiter.pk).update(
                total_resumes_processed=F("total_resumes_processed") + 1
            )
            return {
                "status": "error",
                "message": "Insufficient data extracted from resume (no name or skills)",
                "file_path": file_path,
            }

        profile = temp_profile
        if profile.resume_xml:
            async_task(
                generate_profile_enrichment_task,
                profile.pk,
                task_name=f"generate_candidate_profile_enrichment_{profile.pk}",
            )
        else:
            async_task(
                generate_personal_tagline,
                profile.pk,
                task_name=f"generate_candidate_tagline_{profile.pk}",
            )

        BulkResumeUpload.objects.filter(pk=bulk_pk).update(
            processed_profiles=F("processed_profiles") + 1
        )
        RecruiterProfile.objects.filter(pk=bulk.recruiter.pk).update(
            total_resumes_processed=F("total_resumes_processed") + 1
        )
        BulkResumeUpload.objects.filter(
            pk=bulk_pk, processed_profiles__gte=F("total_files")
        ).delete()

        meta: TaskMeta | None = None
        if meta_pk:
            try:
                meta = TaskMeta.objects.get(pk=meta_pk)
                meta.state = TaskMeta.State.RUNNING
                meta.save(update_fields=["state"])
            except TaskMeta.DoesNotExist:
                meta = None

        if meta:
            meta.state = TaskMeta.State.SUCCESS
            meta.progress = 100
            meta.save(update_fields=["state", "progress"])

        return {
            "status": "success",
            "profile_id": profile.pk,
            "file_processed": os.path.basename(file_path),
            "file_path": file_path,
        }

    except Exception as exc:  # pragma: no cover - defensive
        if meta_pk:
            try:
                meta = TaskMeta.objects.get(pk=meta_pk)
                meta.state = TaskMeta.State.FAILURE
                meta.save(update_fields=["state"])
            except TaskMeta.DoesNotExist:
                pass
        return {
            "status": "error",
            "message": str(exc),
            "file_path": file_path,
        }


@shared_task(name="apps.candidates.tasks.pool_tasks.cleanup_temp_resume_file")
def cleanup_temp_resume_file(result: dict[str, Any] | None = None) -> dict[str, Any]:
    """Delete the temporary resume file created during processing."""
    if not result or not isinstance(result, dict):
        return {"status": "error", "message": "No result provided for cleanup"}

    file_path = result.get("file_path")
    if not file_path:
        return {"status": "error", "message": "No file_path in result for cleanup"}

    if os.path.exists(file_path):
        try:
            os.unlink(file_path)
            return {
                "status": "success",
                "message": f"Successfully cleaned up {file_path}",
                "file_path": file_path,
            }
        except Exception as exc:  # pragma: no cover - defensive
            return {
                "status": "error",
                "message": f"Failed to cleanup {file_path}: {exc}",
                "file_path": file_path,
            }

    return {
        "status": "skipped",
        "message": f"File {file_path} does not exist (already cleaned up?)",
        "file_path": file_path,
    }

