import os
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django_q.models import Task

from apps.core.tasks import safe_async_task
from apps.job_seekers.models import JobSeekerProfile, TalentSheet, UploadedResumePool
from apps.job_seekers.services.profile_manager import ProfileManager
from apps.resume_processing.utils.pipeline import process_resume

# Alias for decoupled task queue
async_task = safe_async_task


def process_resume_for_pool(file_path: str, pool_id: int) -> dict[str, Any]:
    """
    Process a resume for an UploadedResumePool.

    Args:
        file_path: Path to the resume file
        pool_id: ID of the UploadedResumePool

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

        # Build profile data dict
        profile_data = {
            "skills": ProfileManager.format_skills(resume_data.get("skills", [])),
            "experience": resume_data.get("experience", ""),
            "education": resume_data.get("education", ""),
            "certifications": resume_data.get("certifications", ""),
            "years_of_experience": resume_data.get("years_of_experience", 0),
            "most_recent_title": resume_data.get("current_title", ""),
            "professional_summary": resume_data.get("summary", ""),
            "phone": resume_data.get("phone", ""),
            "location": resume_data.get("location", ""),
            "resume_xml": resume_data.get("resume_xml", ""),
        }

        # Create or update the *same* profile (avoids duplicates). Since we saved a
        # profile with this owner above, the manager will return and update that
        # instance instead of creating a new row.
        profile = ProfileManager.create_or_update_profile(resume_pool, profile_data)

        # Generate a TalentSheet for the new profile
        talent_sheet_data = {
            "promotional_blurb": (
                f"Experienced {profile.most_recent_title or 'professional'}"
                f" with {profile.years_of_experience or 'relevant'} years of experience."
            ),
            "skill_overview": (
                f"Key skills include {', '.join(profile.skills_list[:5])}"
                if profile.skills_list
                else "Various competencies"
            ),
            "is_published": True,
        }
        talent_sheet = TalentSheet.objects.create(
            job_seeker=profile, **talent_sheet_data
        )

        # If associated with a JobOpening, trigger matching
        if resume_pool.job_opening:
            async_task(
                "apps.matching.tasks.match_talent_sheet_to_job",
                talent_sheet.pk,
                resume_pool.job_opening.pk,
            )

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
