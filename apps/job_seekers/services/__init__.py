"""
Service layer for job_seekers app.

This package contains business logic services that are independent of the HTTP/presentation layer.
"""

from apps.job_seekers.services.profile_manager import ProfileManager
from apps.job_seekers.services.resume_processing import ResumeProcessor
from apps.job_seekers.services.talent_pool_manager import TalentPoolManager

__all__ = [
    "ProfileManager",
    "ResumeProcessor",
    "TalentPoolManager",
]
