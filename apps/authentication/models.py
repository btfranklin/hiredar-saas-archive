"""Models for the authentication app."""

import inspect
import uuid
import warnings
from typing import Any, TypeVar

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

T = TypeVar("T", bound="User")


class UserManager(BaseUserManager[T]):
    """Custom user manager for the User model."""

    def create_user(
        self, email: str, password: str | None = None, **extra_fields: Any
    ) -> T:
        """Create and save a regular user."""
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

        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields: Any) -> T:
        """Create and save a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if not extra_fields.get("is_staff"):
            raise ValueError(_("Superuser must have is_staff=True."))
        if not extra_fields.get("is_superuser"):
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)

    def create(self, **kwargs: Any) -> T:
        """
        Override the default create method to discourage direct User creation.

        Direct User.objects.create() calls bypass username generation and password hashing.
        Always use User.objects.create_user() instead.
        """

        # Get the calling frame
        frame = inspect.currentframe()
        if frame:
            frame = frame.f_back  # Get the frame that called this method
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

        # If you want to make this a hard error instead of a warning, uncomment the following:
        # raise ValueError("Direct User creation is not allowed. Use User.objects.create_user() instead.")

        # Still allow the creation to proceed (but with a warning)
        return super().create(**kwargs)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model that uses email as the username field."""

    username = models.CharField(_("username"), max_length=150, unique=True)
    email = models.EmailField(_("email address"), unique=True)
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    user_type = models.CharField(
        _("user type"),
        max_length=20,
        choices=[
            ("job_seeker", "Job Seeker"),
            ("recruiter", "Recruiter"),
            ("admin", "Administrator"),
        ],
        default="job_seeker",
    )
    location = models.CharField(_("location"), max_length=100, blank=True)
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

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        """Meta class for User model."""

        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self) -> str:
        """Return string representation of the user."""
        return self.email

    def get_full_name(self) -> str:
        """Return the user's full name."""
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()

    def get_short_name(self) -> str:
        """Return the user's first name."""
        return self.first_name

    def to_dict(self) -> dict[str, Any]:
        """Convert user instance to a dictionary."""
        return {
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "user_type": self.user_type,
            "location": self.location or None,
        }

    def get_initials(self) -> str:
        """Get user initials for avatar display"""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        if self.first_name:
            return self.first_name[0].upper()
        if self.last_name:
            return self.last_name[0].upper()
        return "U"  # Default for users with no name parts

    def get_absolute_url(self) -> str:
        """Get the absolute URL for this user"""
        return reverse("accounts:profile")

    def clean(self) -> None:
        """
        Validate the user object before saving.

        Ensures that only users with user_type 'admin' can have is_staff=True.
        """
        super().clean()
        if self.is_staff and self.user_type != "admin":
            raise ValidationError(
                {"is_staff": "Only administrators can have staff privileges."}
            )
