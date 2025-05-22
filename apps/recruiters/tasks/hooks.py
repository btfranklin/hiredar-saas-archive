"""
Task hook functions for recruiters.

This module contains hook functions that are triggered after task completion
to create task chains and manage next steps in asynchronous processing.
"""

import logging

# Celery compat – see notes in ``job_seekers.tasks.hooks``
from typing import Any

Task = Any  # type: ignore

# Setup logging
logger = logging.getLogger(__name__)


def job_processing_done(task: Task) -> None:
    """
    Hook function executed when job description processing completes.

    This function is triggered after handle_job_description_task completes.
    It checks if the task was successful and can queue additional
    processing tasks if needed.

    Args:
        task: The completed Task object with result and arguments
    """
    logger.info("Job description processing completed hook triggered")

    # Check if the task was successful
    if not task.success:
        logger.error("Job description processing task failed")
        return

    result = task.result
    if not isinstance(result, dict):
        logger.error("Task result is not a dictionary")
        return

    status = result.get("status", "unknown")

    if status == "completed":
        job_id = result.get("job_opening_id")
        logger.info("Job processing completed successfully. Job ID: %s", job_id)

        # Here we could trigger additional tasks such as:
        # - Matching candidates to the new job opening
        # - Sending notifications to recruiters
        # - Updating search indexes

        # Example of how to queue a follow-up task:
        # async_task(
        #     "apps.matching.tasks.match_candidates_to_job",
        #     job_id,
        #     hook="apps.matching.tasks.hooks.matching_completed",
        # )
    else:
        error_msg = result.get("message", "Unknown error")
        logger.error("Job processing failed: %s", error_msg)
