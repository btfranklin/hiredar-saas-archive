"""
Service-layer helpers for resume processing.

This package centralizes orchestration utilities that were previously split
across ``utils`` modules into a single service namespace.
"""

from apps.resume_processing.services.pipeline import process_resume

__all__ = [
    "process_resume",
]
