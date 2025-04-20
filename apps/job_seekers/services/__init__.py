"""
Service layer for job_seekers app.

This package contains business logic services that are independent of the HTTP/presentation layer.

Notable services:
- ProfileManager: Manages JobSeekerProfile entities and provides methods for getting profiles by user
  - get_profile_for_user(user): Get a profile for a user object
  - get_profile_by_user_id(user_id): Get a profile for a user by ID
"""

from apps.job_seekers.services.profile_manager import ProfileManager
from apps.job_seekers.services.talent_pool_manager import TalentPoolManager

__all__ = [
    "ProfileManager",
    "TalentPoolManager",
]
