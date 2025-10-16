"""
Legacy wrapper for resume-processing tasks.

All real task implementations now reside under ``apps.candidates.tasks``.  This
module re-exports them for compatibility with existing imports.
"""

from apps.candidates.tasks.resume_processing.processing import (  # noqa: F401
    handle_resume_upload_task,
    save_resume_file,
)

__all__ = [
    "handle_resume_upload_task",
    "save_resume_file",
]
