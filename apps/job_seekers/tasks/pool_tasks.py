import os
from typing import Any

from celery import shared_task
from django.db.models import F

from apps.core.models import TaskMeta
from apps.core.tasks import safe_async_task
from apps.job_seekers.models import CandidatePool, JobSeekerProfile
from apps.recruiters.models import BulkResumeUpload, RecruiterProfile

# Alias for decoupled task queue
async_task = safe_async_task


@shared_task(name="apps.job_seekers.tasks.pool_tasks.process_resume_for_pool")
def process_resume_for_pool(
    file_path: str, pool_id: int, bulk_pk: int, meta_pk: str | None = None
) -> dict[str, Any]:
    """
    Process a resume for a CandidatePool.

    Args:
        file_path: Path to the resume file
        pool_id: ID of the CandidatePool
        bulk_pk: Primary key of the BulkResumeUpload
        meta_pk: Primary key of the TaskMeta

    Returns:
        Dictionary with processing results including file_path for cleanup
    """
    try:
        candidate_pool = CandidatePool.objects.get(pk=pool_id)
        bulk = BulkResumeUpload.objects.select_related("recruiter").get(pk=bulk_pk)
    except CandidatePool.DoesNotExist:
        return {
            "status": "error",
            "message": f"Resume pool with ID {pool_id} not found",
            "file_path": file_path,
        }

    try:
        # Create a temporary profile owned by the resume pool
        temp_profile = JobSeekerProfile(candidate_pool=candidate_pool)
        # Save immediately so ``process_resume`` can update it atomically
        temp_profile.save()

        # Run the resume-processing pipeline
        # Deferred import to avoid circular import
        from apps.resume_processing.services.pipeline import process_resume

        result = process_resume(file_path, temp_profile, None)

        # If the pipeline itself reported failure, clean up and exit early
        if not result.get("success", False):
            # Delete the temporary – and still blank – profile so we don't keep junk rows
            temp_profile.delete()
            # Mark this file as processed (even though it failed) so we don't hang the bulk record
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

        # Sanity-check the extracted data – avoid keeping junk profiles
        personal = resume_data.get("personal_details", {}) or {}

        # Heuristic: if we did not extract at least a candidate name **or** any skills,
        # consider this resume unusable and discard the profile.  This prevents blank
        # profiles from polluting the candidate pool.
        has_minimum_data = bool(personal.get("name")) or bool(resume_data.get("skills"))

        if not has_minimum_data:
            # Nothing meaningful was parsed – clean up
            temp_profile.delete()
            # Mark this file as processed (even though it failed) so we don't hang the bulk record
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

        # Map parsed_data into profile_data using the correct keys
        profile_data = {
            "skills": resume_data.get("skills", ""),
            "experience": resume_data.get("experience", ""),
            "education": resume_data.get("education", ""),
            "certifications": resume_data.get("certifications", ""),
            "years_of_experience": resume_data.get("years_of_experience", 0),
            "most_recent_title": resume_data.get("most_recent_title", ""),
            "professional_summary": resume_data.get("professional_summary", ""),
            # Save parsed name, phone, location into pool-owned profile
            "candidate_name": personal.get("name", ""),
            "phone": (personal.get("phone", "") or "")[:20],
            "location": (personal.get("location", "") or ""),
        }

        # Update the temporary profile we created for this resume
        for field, value in profile_data.items():
            if hasattr(temp_profile, field):
                setattr(temp_profile, field, value)
        temp_profile.save()
        profile = temp_profile

        # Schedule LLM-powered TalentSheet generation **only** if we have resume XML.
        if profile.resume_xml:
            from apps.job_seekers.tasks.talent_sheet_tasks import (
                generate_talent_sheet_task,
            )

            async_task(
                generate_talent_sheet_task,
                profile.pk,
                task_name=f"generate_talent_sheet_{profile.pk}",
            )

        # Update bulk upload processed_profiles count
        BulkResumeUpload.objects.filter(pk=bulk_pk).update(
            processed_profiles=F("processed_profiles") + 1
        )
        RecruiterProfile.objects.filter(pk=bulk.recruiter.pk).update(
            total_resumes_processed=F("total_resumes_processed") + 1
        )
        # If all profiles processed, delete the bulk upload and associated files
        BulkResumeUpload.objects.filter(
            pk=bulk_pk, processed_profiles__gte=F("total_files")
        ).delete()

        # Prepare TaskMeta reference (may be omitted for historical calls)
        meta: TaskMeta | None = None
        if meta_pk:
            try:
                meta = TaskMeta.objects.get(pk=meta_pk)
                meta.state = TaskMeta.State.RUNNING
                meta.save(update_fields=["state"])
            except TaskMeta.DoesNotExist:
                meta = None

        # Mark task as SUCCESS
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

    except Exception as exc:
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


@shared_task(name="apps.job_seekers.tasks.pool_tasks.cleanup_temp_resume_file")
def cleanup_temp_resume_file(result: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Clean up temporary resume file after processing.

    Args:
        result: Result dictionary from the previous task containing file_path

    Returns:
        Dictionary with cleanup status
    """
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
        except Exception as exc:
            return {
                "status": "error",
                "message": f"Failed to cleanup {file_path}: {str(exc)}",
                "file_path": file_path,
            }
    else:
        return {
            "status": "skipped",
            "message": f"File {file_path} does not exist (already cleaned up?)",
            "file_path": file_path,
        }
