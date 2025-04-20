"""
Task definitions for asynchronous processing in the job_seekers app.

This package contains Django Q2 tasks organized by functional area.
"""

from apps.job_seekers.tasks.hooks import resume_processing_completed
from apps.job_seekers.tasks.personal_tagline_tasks import generate_personal_tagline
from apps.job_seekers.tasks.recommendation_tasks import generate_role_recommendations
from apps.job_seekers.tasks.talent_sheet_tasks import generate_talent_sheet_task

# Import cleanup helpers from canonical resume_processing app
from apps.resume_processing.tasks.cleanup_tasks import (
    cleanup_resume_processing_progress,
    ensure_cleanup_scheduled,
)
from apps.resume_processing.tasks.resume_processing_tasks import (
    handle_resume_upload_task,
    save_resume_file,
)

# Export all tasks at the module level
__all__ = [
    # Resume processing tasks
    "save_resume_file",
    "handle_resume_upload_task",
    # Cleanup tasks
    "cleanup_resume_processing_progress",
    "ensure_cleanup_scheduled",
    # Hook functions
    "resume_processing_completed",
    # Recommendation tasks
    "generate_role_recommendations",
    # Personal tagline tasks
    "generate_personal_tagline",
    # Talent sheet tasks
    "generate_talent_sheet_task",
]
