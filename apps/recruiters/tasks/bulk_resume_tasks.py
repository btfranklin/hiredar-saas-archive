"""Tasks for handling bulk resume uploads."""

from __future__ import annotations

import io
import logging
import zipfile
from typing import Any

from django.core.files.base import ContentFile
from django.db.models import F

# graceful import for runtime, fallback no-op decorator for type-checkers
try:
    from django_q2 import task  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – during linting or docs build

    def task(*_args, **_kwargs):  # type: ignore
        def decorator(func):  # type: ignore
            return func

        return decorator


from apps.recruiters.models import BulkResumeUpload, ResumeFile

logger = logging.getLogger(__name__)


@task()
def unpack_and_process_zip(bulk_pk: int) -> dict[str, Any]:
    """Unpack the ZIP archive and create ResumeFile objects, enqueueing AI pipeline."""

    try:
        bulk = BulkResumeUpload.objects.select_related("recruiter").get(pk=bulk_pk)
    except BulkResumeUpload.DoesNotExist:
        logger.error("BulkResumeUpload not found: pk=%s", bulk_pk)
        return {"status": "error", "message": "bulk upload not found"}

    try:
        # Read zip into memory – in production consider streaming or tmp file for large archives
        data: bytes = bulk.zip_file.read()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            # Only keep real PDF files – skip macOS metadata like __MACOSX/ and dot-underscore files
            names: list[str] = []
            for member in zf.namelist():
                member_lower = member.lower()
                if not member_lower.endswith(".pdf"):
                    continue  # not a PDF
                # Skip macOS resource-fork entries (.___ and __MACOSX directories)
                if member_lower.startswith("__macosx/") or "/__macosx/" in member_lower:
                    continue
                if member_lower.startswith("._") or "/._" in member_lower:
                    continue
                names.append(member)
            bulk.total_files = len(names)
            bulk.save(update_fields=["total_files"])

            for name in names:
                pdf_bytes = zf.read(name)
                # Use only the base filename – strip any path components
                clean_name = name.rsplit("/", 1)[-1]
                resume = ResumeFile.objects.create(
                    bulk_upload=bulk,
                    recruiter=bulk.recruiter,
                    original_filename=clean_name,
                )
                resume.file.save(clean_name, ContentFile(pdf_bytes))
                resume.save()

                # TODO: enqueue AI resume processing pipeline, e.g. resume_processing.enqueue(resume.pk)

                # Increment processed count
                BulkResumeUpload.objects.filter(pk=bulk.pk).update(
                    processed_files=F("processed_files") + 1
                )

        bulk.processed = True
        bulk.save(update_fields=["processed"])
        return {"status": "ok", "processed": bulk.processed_files}

    except Exception as exc:  # pragma: no cover – guard for unexpected
        logger.exception("Error unpacking zip for bulk upload %s: %s", bulk_pk, exc)
        bulk.processed = True
        bulk.save(update_fields=["processed"])
        return {"status": "error", "message": str(exc)}
