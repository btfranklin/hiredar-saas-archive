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
from apps.resume_processing.models import ResumeProcessingJob


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


@receiver(post_save, sender=ResumeProcessingJob)
def deduct_credit_on_success(sender, instance, created, **kwargs):
    """
    Deduct one credit when a resume processing job completes successfully.
    """
    if not created or instance.status != "success":
        return
    try:
        profile = instance.user.recruiter_profile  # type: ignore[attr-defined]
    except Exception:
        return
    # Decrement available credits atomically
    from django.db.models import F

    RecruiterProfile.objects.filter(pk=profile.pk).update(
        credits_available=F("credits_available") - 1
    )
