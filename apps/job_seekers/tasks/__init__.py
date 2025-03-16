"""
Task definitions for asynchronous processing in the job_seekers app.

This package contains Django Q2 tasks organized by functional area.
"""

from apps.job_seekers.tasks.cleanup_tasks import (
    cleanup_resume_processing_progress,
    ensure_cleanup_scheduled,
)
from apps.job_seekers.tasks.hooks import resume_processing_completed
from apps.job_seekers.tasks.recommendation_tasks import (
    generate_personal_tagline,
    generate_role_recommendations,
)
from apps.job_seekers.tasks.resume_processing_tasks import (
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
    "generate_personal_tagline",
]
