"""
Service-layer helpers for resume processing.

This package centralizes orchestration utilities that were previously split
across ``utils`` modules into a single service namespace.
"""

from apps.candidates.services.resume_pipeline import process_resume

__all__ = [
    "process_resume",
]
