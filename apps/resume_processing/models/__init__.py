"""Legacy facade for resume-processing models now living in candidates."""

from apps.candidates.models import (  # noqa: F401
    ResumeProcessingJob,
    ResumeProcessingTaskProgress,
)

__all__ = ["ResumeProcessingTaskProgress", "ResumeProcessingJob"]
