"""
Task definitions for asynchronous processing in the job_seekers app.

This package contains Celery tasks organized by functional area.
"""

from apps.job_seekers.tasks.hooks import resume_processing_completed
from apps.job_seekers.tasks.personal_tagline_tasks import generate_personal_tagline
from apps.job_seekers.tasks.recommendation_tasks import generate_role_recommendations
from apps.job_seekers.tasks.talent_sheet_tasks import generate_talent_sheet_task
from apps.resume_processing.tasks.cleanup_tasks import (
    cleanup_resume_processing_progress,
)
from apps.resume_processing.tasks.resume_processing_tasks import (
    handle_resume_upload_task,
    save_resume_file,
)

from .pool_tasks import cleanup_temp_resume_file, process_resume_for_pool

__all__ = [
    "save_resume_file",
    "handle_resume_upload_task",
    "cleanup_resume_processing_progress",
    "resume_processing_completed",
    "generate_role_recommendations",
    "generate_personal_tagline",
    "generate_talent_sheet_task",
    "process_resume_for_pool",
    "cleanup_temp_resume_file",
]
