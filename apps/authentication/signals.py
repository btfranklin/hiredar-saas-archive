"""
Signal handlers for the authentication app.

This module contains signal handlers for User model.
"""

from typing import Any, Type

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.authentication.models import User


@receiver(post_save, sender=User)
def user_post_save(
    sender: Type[User], instance: User, created: bool, **kwargs: dict[str, Any]
) -> None:
    """
    Handle post-save signal for User model.

    Args:
        sender: The model class (User)
        instance: The actual instance being saved
        created: Boolean; True if a new record was created
        **kwargs: Additional keyword arguments
    """
    # Currently no post-save actions needed for User model


@receiver(pre_save, sender=User)
def enforce_staff_privileges(
    sender: Type[User], instance: User, **kwargs: dict[str, Any]
) -> None:
    """
    Enforce rules for staff privileges.

    Ensures that only users with user_type 'admin' can have staff privileges.
    If a user is given staff privileges, their user_type is automatically set to 'admin'.
    """
    if instance.is_staff and instance.user_type != "admin":
        instance.user_type = "admin"
