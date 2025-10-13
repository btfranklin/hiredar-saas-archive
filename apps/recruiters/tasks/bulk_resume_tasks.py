"""Tasks for handling bulk resume uploads."""

from __future__ import annotations

import io
import logging
import os
import tempfile
import zipfile
from typing import Any

from celery import chain, shared_task
from django.core.files.base import ContentFile

from apps.core.models import TaskMeta
from apps.core.tasks import safe_async_task
from apps.job_seekers.models.profile import CandidatePool
from apps.job_seekers.tasks.pool_tasks import (
    cleanup_temp_resume_file,
    process_resume_for_pool,
)
from apps.recruiters.models import BulkResumeUpload, ResumeFile
from apps.resume_processing.services.extraction import (
    SUPPORTED_RESUME_EXTENSIONS,  # local import to avoid cycles
)

logger = logging.getLogger(__name__)

# Alias for decoupled task queue
async_task = safe_async_task


@shared_task(name="apps.recruiters.tasks.bulk_resume_tasks.unpack_and_process_zip")
def unpack_and_process_zip(
    bulk_pk: int, pool_id: int | None = None, meta_pk: str | None = None
) -> dict[str, Any]:
    """Unpack the ZIP archive and create ResumeFile objects, enqueueing AI pipeline."""

    try:
        bulk = BulkResumeUpload.objects.select_related("recruiter").get(pk=bulk_pk)
    except BulkResumeUpload.DoesNotExist:
        logger.error("BulkResumeUpload not found: pk=%s", bulk_pk)
        return {"status": "error", "message": "bulk upload not found"}

    try:
        # Handle placeholder TaskMeta if provided
        placeholder_meta: TaskMeta | None = None
        if meta_pk:
            try:
                placeholder_meta = TaskMeta.objects.get(pk=meta_pk)
                placeholder_meta.state = TaskMeta.State.RUNNING
                placeholder_meta.save(update_fields=["state"])
            except TaskMeta.DoesNotExist:
                placeholder_meta = None

        # Use existing CandidatePool if provided (created synchronously so the
        # dashboard can show a placeholder immediately). Otherwise create it
        # here just like before.
        if pool_id is not None:
            candidate_pool = CandidatePool.objects.get(pk=pool_id)
        else:
            candidate_pool = CandidatePool.objects.create(
                recruiter=bulk.recruiter.user,  # CandidatePool expects a User
                name=bulk.name,
            )

        # ------------------------------------------------------------------
        # Unpack the ZIP and create ResumeFile objects
        # ------------------------------------------------------------------
        # Read zip into memory – in production consider streaming or tmp file for large archives
        data: bytes = bulk.zip_file.read()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            # Keep only real resume files – skip macOS metadata like __MACOSX/ and dot-underscore files
            names: list[str] = []
            for member in zf.namelist():
                member_lower = member.lower()

                # Skip directories and macOS resource-fork entries early
                if member_lower.endswith("/"):
                    continue  # directory entry
                if member_lower.startswith("__macosx/") or "/__macosx/" in member_lower:
                    continue
                if member_lower.startswith("._") or "/._" in member_lower:
                    continue

                # Check extension against supported list
                ext = (
                    ("." + member_lower.rsplit(".", 1)[-1])
                    if "." in member_lower
                    else ""
                )
                if ext not in SUPPORTED_RESUME_EXTENSIONS:
                    continue

                names.append(member)
            bulk.total_files = len(names)
            bulk.save(update_fields=["total_files"])

            if not names:
                logger.info(
                    "No valid resumes found in ZIP %s; deleting bulk upload", bulk_pk
                )
                bulk.delete()
                if placeholder_meta:
                    placeholder_meta.state = TaskMeta.State.SUCCESS
                    placeholder_meta.progress = 100
                    placeholder_meta.save(update_fields=["state", "progress"])
                return {"status": "empty", "processed_profiles": 0}

            for name in names:
                file_bytes = zf.read(name)
                # Use only the base filename – strip any path components
                clean_name = name.rsplit("/", 1)[-1]
                resume = ResumeFile.objects.create(
                    bulk_upload=bulk,
                    recruiter=bulk.recruiter,
                    original_filename=clean_name,
                )
                resume.file.save(clean_name, ContentFile(file_bytes))
                resume.save()

                # Preserve extension so downstream validators / libraries have context
                suffix = os.path.splitext(clean_name)[1] or ".tmp"
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=suffix
                ) as tmp_file:
                    tmp_file.write(file_bytes)
                    tmp_file.flush()
                local_path = tmp_file.name

                # ------------------------------------------------------
                # Create TaskMeta row *before* scheduling the async task so we
                # can store its primary key inside the payload.
                # ------------------------------------------------------

                task_id = f"resume-{resume.pk}"

                meta = TaskMeta.objects.create(
                    queue_id=task_id,
                    name="Processing resume",  # could include filename if desired
                    owner=bulk.recruiter.user,
                    content_object=candidate_pool,
                    state=TaskMeta.State.PENDING,
                )

                # Schedule per-resume processing using Celery chain for cleanup
                process_task = process_resume_for_pool.si(  # type: ignore[misc]
                    local_path,
                    candidate_pool.pk,
                    bulk.pk,
                    str(meta.pk),
                )
                cleanup_task = cleanup_temp_resume_file.s()  # type: ignore[misc]

                # Create and execute the chain
                task_chain = chain(process_task, cleanup_task)
                async_result = task_chain.apply_async()

                # Back-link the TaskMeta row to the actual queue id
                if async_result and async_result.id:
                    meta.queue_id = async_result.id
                    meta.save(update_fields=["queue_id"])

        bulk.processed = True
        bulk.save(update_fields=["processed"])

        if placeholder_meta:
            placeholder_meta.state = TaskMeta.State.SUCCESS
            placeholder_meta.progress = 100
            placeholder_meta.save(update_fields=["state", "progress"])
        return {"status": "ok", "processed_profiles": bulk.processed_profiles}

    except Exception as exc:  # pragma: no cover – guard for unexpected
        logger.exception("Error unpacking zip for bulk upload %s: %s", bulk_pk, exc)
        if placeholder_meta:
            placeholder_meta.state = TaskMeta.State.FAILURE
            placeholder_meta.save(update_fields=["state"])
        bulk.processed = True
        bulk.save(update_fields=["processed"])
        return {"status": "error", "message": str(exc)}
