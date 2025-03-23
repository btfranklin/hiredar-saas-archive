"""
Task functions for the recruiters app.

This package contains asynchronous task functions for processing job descriptions,
creating job openings, and other recruiter-related functionality.
"""

# Import tasks from modules for easy access
from apps.recruiters.tasks.job_processing_tasks import (
    handle_job_description_task,
    job_processing_done,
)

# Export all task functions
__all__ = [
    "handle_job_description_task",
    "job_processing_done",
]
