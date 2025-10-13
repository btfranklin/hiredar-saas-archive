"""Aggregate resume-processing models used across services and tasks."""

from .resume_processing_job import ResumeProcessingJob
from .resume_processing_task_progress import ResumeProcessingTaskProgress

__all__ = [
    "ResumeProcessingTaskProgress",
    "ResumeProcessingJob",
]
