"""Authentication models."""

from __future__ import annotations

import inspect
import uuid
import warnings
from typing import Any, TypeVar

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.authentication.validators import validate_recruiter_name

T = TypeVar("T", bound="User")


class UserManager(BaseUserManager[T]):
    """Custom user manager for the User model."""

    def create_user(
        self, email: str, password: str | None = None, **extra_fields: Any
    ) -> T:
        """Create and save a regular user."""
        if password is None:
            raise ValueError("A password must be provided when creating users.")
        if not email:
            raise ValueError(_("The Email field must be set"))
        email = self.normalize_email(email)

        # Generate username if not provided
        if "username" not in extra_fields:
            # Create a username based on email
            base_username = email.split("@")[0]
            # Truncate to ensure it fits within max_length with uuid
            if len(base_username) > 10:
                base_username = base_username[:10]
            # Add unique suffix to ensure uniqueness
            username = f"{base_username}_{str(uuid.uuid4())[:8]}"
            extra_fields["username"] = username

        # Set default name if not provided
        if "name" not in extra_fields:
            extra_fields["name"] = "New User"

        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields: Any) -> T:
        """Create and save a superuser."""
        extra_fields.setdefault("user_type", "admin")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if not extra_fields.get("is_staff"):
            raise ValueError(_("Superuser must have is_staff=True."))
        if not extra_fields.get("is_superuser"):
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)

    def create(self, **kwargs: Any) -> T:
        """Discourage direct User.objects.create() calls."""
        frame = inspect.currentframe()
        if frame:
            frame = frame.f_back
            if frame:
                filename = frame.f_code.co_filename
                lineno = frame.f_lineno
                caller = f"{filename}:{lineno}"
            else:
                caller = "unknown location"
        else:
            caller = "unknown location"

        warnings.warn(
            f"Direct User.objects.create() called from {caller}. "
            "This bypasses username generation and proper password hashing. "
            "Use User.objects.create_user() instead.",
            UserWarning,
            stacklevel=2,
        )
        return super().create(**kwargs)

    # The native BaseUserManager.create_superuser will call full_clean and
    # trigger the AUTH_PASSWORD_VALIDATORS settings which we do not want
    # for programmatic superuser creation. Keep the base behaviour.


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model that uses email as the username field."""

    username = models.CharField(_("username"), max_length=150, unique=True)
    email = models.EmailField(_("email address"), unique=True)
    name = models.CharField(
        _("name"),
        max_length=255,
        default="New User",
        validators=[validate_recruiter_name],
    )
    user_type = models.CharField(
        _("user type"),
        max_length=20,
        choices=[
            ("job_seeker", "Job Seeker"),
            ("recruiter", "Recruiter"),
            ("admin", "Administrator"),
        ],
        default="recruiter",
    )
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    date_joined = models.DateTimeField(_("date joined"), auto_now_add=True)
    timezone = models.CharField(
        _("timezone"),
        max_length=50,
        default="UTC",
        help_text=_(
            "Preferred IANA timezone name for this user (e.g. 'Europe/Paris')."
        ),
    )
    is_us_certified = models.BooleanField(
        _("US certified"),
        default=False,
        help_text=_(
            "Indicates that the user has confirmed they are physically located in the "
            "United States and will use the platform solely for US-based hiring "
            "activities."
        ),
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        indexes = [
            GinIndex(
                name="user_name_trgm",
                fields=["name"],
                opclasses=["gin_trgm_ops"],
            ),
        ]

    def __str__(self) -> str:
        return self.email

    def get_full_name(self) -> str:
        return self.name

    def get_short_name(self) -> str:
        return self.name

    def to_dict(self) -> dict[str, Any]:
        return {
            "email": self.email,
            "name": self.name,
            "user_type": self.user_type,
        }

    def get_initials(self) -> str:
        parts = self.name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        if len(parts) == 1 and parts[0]:
            return parts[0][0].upper()
        return "U"

    def get_absolute_url(self) -> str:
        return reverse("accounts:profile")

    def clean(self) -> None:
        super().clean()
        if self.is_staff and self.user_type != "admin":
            raise ValidationError(
                {"is_staff": "Only administrators can have staff privileges."}
            )
        if self.user_type == "admin" and not self.is_superuser:
            raise ValidationError(
                {
                    "is_superuser": (
                        "Administrator accounts must have superuser privileges "
                        "(is_superuser=True)."
                    )
                }
            )

    def get_unread_notifications_count(self) -> int:
        return 0

    def get_recent_notifications(self, _limit: int = 5):
        return []
