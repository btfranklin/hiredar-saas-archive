"""
Task hook functions for job seekers.

This module contains hook functions that are triggered after task completion
to create task chains and manage next steps in asynchronous processing.
"""

import logging

from django_q.tasks import Task, async_task

# Setup logging
logger = logging.getLogger(__name__)


def resume_processing_completed(task: Task) -> None:
    """
    Hook function executed when resume processing completes.

    This function is triggered after handle_resume_upload_task completes.
    It checks if the task was successful, and if so, queues additional
    processing tasks that can run in parallel.

    Args:
        task: The completed Task object with result and arguments
    """
    logger.info("Resume processing completed hook triggered")

    # Check if the task was successful
    if not task.success:
        logger.error("Resume processing task failed, not starting follow-up tasks")
        return

    result = task.result
    if not isinstance(result, dict) or not result.get("success", False):
        logger.error(
            "Resume processing did not return success result, not starting follow-up tasks"
        )
        return

    # Get the job seeker profile ID from the original task arguments
    if len(task.args) < 2:
        logger.error("Cannot find profile ID in task args")
        return

    profile_id = task.args[1]
    logger.info("Starting follow-up tasks for profile ID: %s", profile_id)

    # Start multiple follow-up tasks individually for now
    # We'll use a common group name to logically group them
    group_name = f"resume_followup_{profile_id}"

    # Generate role recommendations
    rec_task_id = async_task(
        "apps.job_seekers.tasks.recommendation_tasks.generate_role_recommendations",
        profile_id,
        group=group_name,
    )

    # Generate personal tagline
    tagline_task_id = async_task(
        "apps.job_seekers.tasks.recommendation_tasks.generate_personal_tagline",
        profile_id,
        group=group_name,
    )

    logger.info(
        "Started follow-up tasks with IDs: %s, %s (group: %s)",
        rec_task_id,
        tagline_task_id,
        group_name,
    )

    # Note: The group feature would be implemented here in a more advanced version
    # For simplicity, we're not using the full group functionality


def all_processing_complete(group_result: list[Task]) -> None:
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
