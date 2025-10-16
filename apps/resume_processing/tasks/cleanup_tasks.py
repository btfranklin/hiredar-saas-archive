"""
Legacy wrapper for resume-processing cleanup tasks.

The implementation now lives under ``apps.candidates.tasks``.  This module keeps
the historic import path functioning while the resume_processing app is being
decommissioned.
"""

from apps.candidates.tasks.resume_processing.cleanup import (  # noqa: F401
    cleanup_resume_processing_progress,
)

__all__ = ["cleanup_resume_processing_progress"]
