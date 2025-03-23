"""Admin configuration for the authentication app."""

from typing import Any, cast

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import HttpRequest

from apps.authentication.forms import CustomUserChangeForm, CustomUserCreationForm
from apps.authentication.models import User
from apps.authentication.types import AuthenticatedUser


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Admin configuration for the custom User model."""

    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    list_display = (
        "email",
        "name",
        "username",
        "user_type",
        "is_staff",
        "is_active",
    )
    list_filter = ("user_type", "is_staff", "is_active")
    readonly_fields = ("username",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("name",)}),
        ("System info", {"fields": ("username",)}),
        ("User type", {"fields": ("user_type",)}),
        (
            "Permissions",
            {
                "fields": (
                    "is_staff",
                    "is_active",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "name",
                    "user_type",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )
    search_fields = ("email", "name", "username")
    ordering = ("email",)

    def get_queryset(self, request: HttpRequest) -> Any:
        """Get the queryset for the admin view."""
        queryset = super().get_queryset(request)
        user = cast(AuthenticatedUser, request.user)

        # Staff users can see all users
        if user.is_staff:
            return queryset

        # Non-staff users can only see their own profile
        return queryset.filter(pk=user.pk)

    def has_view_permission(
        self, request: HttpRequest, obj: User | None = None
    ) -> bool:
        """Check if user has permission to view the object."""
        user = cast(AuthenticatedUser, request.user)

        # Staff users can view all users
        if user.is_staff:
            return True

        # Non-staff users can only view their own profile
        return obj is not None and obj.pk == user.pk

    def has_change_permission(
        self, request: HttpRequest, obj: User | None = None
    ) -> bool:
        """Check if user has permission to change the object."""
        user = cast(AuthenticatedUser, request.user)

        # Staff users can change all users
        if user.is_staff:
            return True

        # Non-staff users can only change their own profile
        return obj is not None and obj.pk == user.pk

    def has_delete_permission(
        self, request: HttpRequest, obj: User | None = None
    ) -> bool:
        """Check if user has permission to delete the object."""
        user = cast(AuthenticatedUser, request.user)

        # Only staff users can delete users
        return user.is_staff

    def save_model(
        self, request: HttpRequest, obj: User, form: Any, change: bool
    ) -> None:
        """
        Custom save_model to enforce business rules.

        Ensures that only users with user_type 'admin' can have staff privileges.
        """
        # If the user is being given staff privileges, ensure they're an admin
        if obj.is_staff and obj.user_type != "admin":
            # Automatically set user_type to admin if giving staff privileges
            obj.user_type = "admin"

        super().save_model(request, obj, form, change)
