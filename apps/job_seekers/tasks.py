"""
Background tasks for the job_seekers app.
"""

import os
from typing import Any

from django.contrib.contenttypes.models import ContentType

from apps.core.tasks import safe_async_task
from apps.job_seekers.models import JobSeekerProfile, TalentSheet, UploadedResumePool
from apps.job_seekers.services.profile_manager import ProfileManager
from apps.resume_processing.utils.pipeline import process_resume

async_task = safe_async_task


def process_resume_for_pool(
    file_path: str, pool_id: int, task_id: str
) -> dict[str, Any]:
    """
    Process a resume for an UploadedResumePool.

    Args:
        file_path: Path to the resume file
        pool_id: ID of the UploadedResumePool
        task_id: Task ID for tracking

    Returns:
        Dictionary with processing results
    """
    # Get the resume pool
    try:
        resume_pool = UploadedResumePool.objects.get(pk=pool_id)
    except UploadedResumePool.DoesNotExist:
        return {"success": False, "error": f"Resume pool with ID {pool_id} not found"}

    # Process the resume file
    try:
        # Create a temporary profile for processing
        owner_content_type = ContentType.objects.get_for_model(
            resume_pool.recruiter.__class__
        )
        temp_profile = JobSeekerProfile(
            owner_content_type=owner_content_type,
            owner_object_id=resume_pool.recruiter.pk,
        )

        # Extract data from resume using the process_resume pipeline
        result = process_resume(file_path, temp_profile, task_id)

        if not result["success"]:
            return {"success": False, "error": "Failed to extract data from resume"}

        resume_data = result.get("profile_data", {})

        # Create a profile for this resume in the pool
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

        # Create profile with pool as owner
        profile = ProfileManager.create_or_update_profile(resume_pool, profile_data)

        # Create a talent sheet for this profile (published by default since it's from a pool)
        talent_sheet_data = {
            "promotional_blurb": f"Experienced {profile.most_recent_title or 'professional'} with {profile.years_of_experience or 'relevant'} years of experience.",
            "skill_overview": f"Key skills include {', '.join(profile.skills_list[:5]) if profile.skills_list else 'various technical competencies'}.",
            "is_published": True,
        }

        # Create talent sheet for the profile
        talent_sheet = TalentSheet.objects.create(
            job_seeker=profile, **talent_sheet_data
        )

        # If the pool has an associated job opening, we could also create a candidate match here
        if resume_pool.job_opening:
            # Trigger matching task
            async_task(
                "apps.matching.tasks.match_talent_sheet_to_job",
                talent_sheet.pk,
                resume_pool.job_opening.pk,
            )

        return {
            "success": True,
            "profile_id": profile.pk,
            "file_processed": os.path.basename(file_path),
            "file_path": file_path,  # Add the file path for cleanup hook
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def cleanup_temp_resume_file(task_result: dict) -> None:
    """
    Clean up temporary resume file after processing.

    Args:
        task_result: Result from the resume processing task
    """
    # The task result should contain the file path
    file_path = task_result.get("file_path")
    if file_path and os.path.exists(file_path):
        try:
            os.unlink(file_path)
        except Exception:
            # Just log and continue if deletion fails
            pass
