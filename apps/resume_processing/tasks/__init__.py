"""
Legacy facade for resume-processing Celery tasks.

All task implementations now live under ``apps.candidates.tasks`` while this
module re-exports them to avoid breaking existing imports during the gradual
deprecation of the ``resume_processing`` app.
"""

from apps.candidates.tasks.resume_processing import (  # noqa: F401
    cleanup_resume_processing_progress,
    handle_resume_upload_task,
    save_resume_file,
)

__all__ = [
    "cleanup_resume_processing_progress",
    "handle_resume_upload_task",
    "save_resume_file",
]
