"""
Job processing tasks for recruiters.

This module contains Django Q async tasks for processing job descriptions
and creating job openings from text.
"""

import logging
from typing import Any

# Setup logging
logger = logging.getLogger(__name__)


# This function is called directly by the Django Q async_task mechanism
# The parameter names must match what's passed to async_task
def job_processing_done(task: dict[str, Any]) -> None:
    """
    Callback function when job processing is complete.

    This function is called by Django Q when the job processing task completes,
    whether successfully or with an error.

    Args:
        task: Task result dictionary from Django Q
    """
    result = task.get("result", {})
    status = result.get("status", "unknown")

    if status == "completed":
        job_id = result.get("job_opening_id")
        logger.info("Job processing completed successfully. Job ID: %s", job_id)
    else:
        error_msg = result.get("message", "Unknown error")
        logger.error("Job processing failed: %s", error_msg)

    # Additional post-processing could be added here if needed
    # For example, sending notifications to the recruiter
