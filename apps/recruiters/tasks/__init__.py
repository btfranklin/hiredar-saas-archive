"""
Task functions for the recruiters app.

This package contains asynchronous task functions for processing job descriptions,
creating job openings, and other recruiter-related functionality.
"""

# Import tasks from modules for easy access
from apps.recruiters.tasks.job_processing_tasks import (
    job_processing_done,
    process_job_description,
)

# Export all task functions
__all__ = [
    "process_job_description",
    "job_processing_done",
]
