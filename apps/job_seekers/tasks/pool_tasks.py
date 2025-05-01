import os
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.db.models import F
from django_q.models import Task

from apps.core.tasks import safe_async_task
from apps.job_seekers.models import JobSeekerProfile, UploadedResumePool
from apps.recruiters.models import BulkResumeUpload, RecruiterProfile
from apps.resume_processing.utils.pipeline import process_resume

# Alias for decoupled task queue
async_task = safe_async_task


def process_resume_for_pool(
    file_path: str, pool_id: int, bulk_pk: int
) -> dict[str, Any]:
    """
    Process a resume for an UploadedResumePool.

    Args:
        file_path: Path to the resume file
        pool_id: ID of the UploadedResumePool
        bulk_pk: Primary key of the BulkResumeUpload

    Returns:
        Dictionary with processing results
    """
    try:
        resume_pool = UploadedResumePool.objects.get(pk=pool_id)
    except UploadedResumePool.DoesNotExist:
        return {"success": False, "error": f"Resume pool with ID {pool_id} not found"}

    try:
        # Create a temporary profile owned by the *resume_pool* so we don't mutate the recruiter
        owner_content_type = ContentType.objects.get_for_model(resume_pool.__class__)
        temp_profile = JobSeekerProfile(
            owner_content_type=owner_content_type,
            owner_object_id=resume_pool.pk,
        )
        # Save immediately so ``process_resume`` can update it atomically
        temp_profile.save()

        # Run the unified resume-processing pipeline without progress-tracker integration
        # to avoid noisy "Progress tracker not found" logs for bulk uploads
        result = process_resume(file_path, temp_profile, None)
        if not result.get("success", False):
            return {"success": False, "error": result.get("message", "Failed to process resume")}  # type: ignore

        resume_data = result.get("profile_data", {})

        # Map parsed_data into profile_data using the correct keys
        personal = resume_data.get("personal_details", {}) or {}
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

        # Schedule LLM-powered TalentSheet generation for this pool profile
        async_task(
            "apps.job_seekers.tasks.talent_sheet_tasks.generate_talent_sheet_task",
            profile.pk,
            task_name=f"generate_talent_sheet_{profile.pk}",
        )

        # Update bulk upload processed_profiles count
        BulkResumeUpload.objects.filter(pk=bulk_pk).update(
            processed_profiles=F("processed_profiles") + 1
        )
        # If all profiles processed, delete the bulk upload and associated files
        BulkResumeUpload.objects.filter(
            pk=bulk_pk, processed_profiles__gte=F("total_files")
        ).delete()
        # Deduct one credit from the recruiter for each processed resume
        try:
            RecruiterProfile.objects.filter(user=resume_pool.recruiter).update(
                credits_available=F("credits_available") - 1
            )
        except Exception:
            pass

        return {
            "success": True,
            "profile_id": profile.pk,
            "file_processed": os.path.basename(file_path),
            "file_path": file_path,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def cleanup_temp_resume_file(task: Task) -> None:
    """
    Clean up temporary resume file after processing.

    Args:
        task: Task model instance containing the result dict from resume processing
    """
    # Extract the file_path from the Task result payload
    result_data = task.result or {}
    file_path = result_data.get("file_path") if isinstance(result_data, dict) else None
    if file_path and os.path.exists(file_path):
        try:
            os.unlink(file_path)
        except Exception:
            pass
