"""
Signal handlers for the authentication app.

This module contains signal handlers for User model.
"""

import inspect
import warnings
from typing import Any, Type

from django.contrib.auth.hashers import is_password_usable
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from apps.authentication.models import User


@receiver(post_save, sender=User)
def user_post_save(
    _sender: Type[User], _instance: User, _created: bool, **_kwargs: Any
) -> None:
    """Placeholder hook for user post-save logic."""
    return


@receiver(pre_save, sender=User)
def enforce_staff_privileges(
    _sender: Type[User], instance: User, **_kwargs: Any
) -> None:
    """
    Enforce rules for staff privileges.

    Ensures that only users with user_type 'admin' can have staff privileges.
    If a user is given staff privileges, their user_type is automatically set to 'admin'.
    """
    if instance.is_staff and instance.user_type != "admin":
        instance.user_type = "admin"


@receiver(pre_save, sender=User)
def check_proper_user_creation(
    _sender: Type[User], instance: User, **_kwargs: Any
) -> None:
    """
    Check if a user is being created with a usable password.

    If not, this might indicate the user is being created directly without
    using User.objects.create_user().
    """
    # Only run this check during creation (not updates)
    if instance._state.adding:  # pylint: disable=protected-access
        # Check if the password is properly hashed
        if instance.password and not is_password_usable(instance.password):
            # Get the calling frame for better error messages
            frame = inspect.currentframe()
            if frame:
                for f in inspect.getouterframes(frame):
                    # Skip frames from Django internals and this signal
                    if "django/db" not in f.filename and "signals.py" not in f.filename:
                        caller = f"{f.filename}:{f.lineno}"
                        break
                else:
                    caller = "unknown location"
            else:
                caller = "unknown location"

            warnings.warn(
                f"Potential improper User creation detected from {caller}. "
                "The password does not appear to be properly hashed. "
                "Use User.objects.create_user() to ensure proper user creation.",
                UserWarning,
                stacklevel=2,
            )
