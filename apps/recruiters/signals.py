"""
Signal handlers for the recruiters app.

This module contains signal handlers for automatically creating and managing
RecruiterProfile instances when User instances are created or modified.
"""

from typing import Any, Type

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.authentication.models import User
from apps.recruiters.models import RecruiterProfile


@receiver(post_save, sender=User)
def create_recruiter_profile(
    sender: Type[User], instance: User, created: bool, **kwargs: dict[str, Any]
) -> None:
    """
    Create a RecruiterProfile when a recruiter User is created.

    Args:
        sender: The model class (User)
        instance: The actual instance being saved
        created: Boolean; True if a new record was created
        **kwargs: Additional keyword arguments
    """
    if created and instance.user_type == "recruiter":
        RecruiterProfile.objects.create(user=instance)
