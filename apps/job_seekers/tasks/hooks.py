"""
Task functions for job seekers.

This module contains Celery tasks for handling completion workflows
and managing next steps in asynchronous processing chains.
"""

import logging
from typing import Any

from celery import shared_task

from apps.core.tasks import safe_async_task
from apps.job_seekers.models.profile import JobSeekerProfile
from apps.job_seekers.tasks.recommendation_tasks import generate_role_recommendations
from apps.resume_processing.models import ResumeProcessingJob
from apps.resume_processing.tasks.cleanup_tasks import (
    cleanup_resume_processing_progress,
)

# Setup logging
logger = logging.getLogger(__name__)

# Alias safe_async_task as async_task
async_task = safe_async_task


@shared_task(name="apps.job_seekers.tasks.hooks.resume_processing_completed")
def resume_processing_completed(
    result: dict[str, Any] | None = None,
    profile_id: int | None = None,
    file_path: str | None = None,
) -> dict[str, Any]:
    """
    Task executed when resume processing completes.

    This task is triggered after handle_resume_upload_task completes.
    It checks if the task was successful, and if so, records the job
    and queues additional processing tasks that can run in parallel.

    Args:
        result: The result dictionary from the previous task
        profile_id: The JobSeekerProfile ID (for direct calls)
        file_path: The file path (for direct calls)

    Returns:
        dict: Status and results of the completion processing
    """
    logger.info("Resume processing completed task triggered")

    # Handle different input types for chain flexibility
    if isinstance(result, dict):
        if result.get("status") != "success":
            logger.error(
                "Resume processing did not return success status: %s",
                result.get("status"),
            )
            return {
                "status": "error",
                "message": "Previous task failed, not starting follow-up tasks",
                "result": result,
            }
        # Extract profile_id from result if not provided directly
        if profile_id is None:
            profile_id = result.get("profile_id")
    elif result is None and profile_id is None:
        return {"status": "error", "message": "No result or profile_id provided"}

    if profile_id is None:
        return {"status": "error", "message": "Cannot find profile ID in input"}

    try:
        profile = JobSeekerProfile.objects.get(id=profile_id)

        # Record the resume processing job for quota tracking
        if profile.user_owner:
            job_status = (
                "success"
                if (isinstance(result, dict) and result.get("status") == "success")
                else "failed"
            )
            ResumeProcessingJob.objects.create(
                user=profile.user_owner,
                job_seeker_profile=profile,
                status=job_status,
            )
            logger.info(
                "Created ResumeProcessingJob for user-owned profile %s", profile_id
            )

        logger.info("Starting follow-up tasks for profile ID: %s", profile_id)

        # Only generate role recommendations if the profile has a user_owner
        if profile.user_owner:
            logger.info(
                "Profile %s is owned by a user, generating role recommendations",
                profile_id,
            )

            # Generate role recommendations with semantic naming
            rec_task_id = async_task(
                generate_role_recommendations,
                profile_id,
                task_name=f"role_recommendations_{profile_id}",
            )

            logger.info(
                "Queued role recommendations task with ID: %s",
                rec_task_id,
            )

            # Perform ad-hoc cleanup of stale progress records
            try:
                cleanup_resume_processing_progress()
            except Exception as e:
                logger.error("Error running ad-hoc cleanup: %s", e)

            return {
                "status": "success",
                "message": "Follow-up tasks queued for user-owned profile",
                "profile_id": profile_id,
                "role_recommendations_task_id": rec_task_id,
                "user_owned": True,
            }
        else:
            logger.info(
                "Profile %s is owned by a pool, skipping role recommendations",
                profile_id,
            )
            return {
                "status": "success",
                "message": "Profile is pool-owned, no follow-up tasks needed",
                "profile_id": profile_id,
                "user_owned": False,
            }

    except JobSeekerProfile.DoesNotExist:
        error_msg = f"Profile with ID {profile_id} does not exist"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg, "profile_id": profile_id}
    except Exception as e:
        error_msg = f"Error in resume processing completion: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "message": error_msg, "profile_id": profile_id}


def all_processing_complete(group_result: list[Any]) -> None:
    """
    Hook function executed when all processing tasks are complete.

    This function is triggered after all follow-up tasks have completed.
    It can be used to send notifications or perform final cleanup actions.

    Args:
        group_result: List of Task objects with results
    """
    if not group_result:
        logger.error("Empty group result, cannot process")
        return

    # Extract profile ID from first task in group
    profile_id = None
    for task in group_result:
        if task.args:
            profile_id = task.args[0]
            break

    if not profile_id:
        logger.error("Could not determine profile ID from group result")
        return

    # Check if any tasks failed
    failed_tasks = [t for t in group_result if not t.success]
    if failed_tasks:
        logger.warning(
            "%d of %d tasks failed for profile ID %s",
            len(failed_tasks),
            len(group_result),
            profile_id,
        )

    logger.info(
        "All processing complete for profile ID %s (%d tasks)",
        profile_id,
        len(group_result),
    )

    # Here we could send a notification or trigger a final action
    # For example:
    # async_task('apps.job_seekers.tasks.notification_tasks.send_processing_complete_notification', profile_id)
