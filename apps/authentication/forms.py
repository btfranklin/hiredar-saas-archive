"""Forms for user authentication and registration."""

from typing import Any, cast

from allauth.account.forms import LoginForm
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserChangeForm,
    UserCreationForm,
)
from django.http import HttpRequest

from apps.authentication.models import User
from apps.authentication.types import AuthenticatedUser


class CustomUserCreationForm(UserCreationForm):
    """Form for creating new users."""

    class Meta:
        """Meta class for CustomUserCreationForm."""

        model = User
        fields = ("email", "first_name", "last_name", "user_type")

    def clean(self) -> dict[str, Any]:
        """Clean and validate the form data."""
        cleaned_data = super().clean()
        # Ensure cleaned_data is not None before proceeding
        if cleaned_data is None:
            return {}

        user_type = cleaned_data.get("user_type")

        if user_type not in ["job_seeker", "recruiter"]:
            raise forms.ValidationError("Invalid user type")

        return cleaned_data


class CustomUserChangeForm(UserChangeForm):
    """Form for updating user information."""

    class Meta:
        """Meta class for CustomUserChangeForm."""

        model = User
        fields = ("email", "first_name", "last_name", "location")


class CustomAuthenticationForm(AuthenticationForm):
    """
    Custom authentication form that uses email for authentication.
    """

    username = forms.EmailField(widget=forms.EmailInput(attrs={"autofocus": True}))
    remember = forms.BooleanField(required=False, initial=False)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the form with request for authentication."""
        super().__init__(*args, **kwargs)

        # Change field label from 'Username' to 'Email'
        self.fields["username"].label = "Email"

        # Apply styling to form fields
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"

    def clean(self) -> dict[str, Any]:
        """Authenticate using email as username."""
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username is not None and password:
            self.user_cache = authenticate(
                request=self.request, username=username, password=password
            )
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages["invalid_login"],
                    code="invalid_login",
                )
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class SignupForm(forms.Form):
    """Form for user signup."""

    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    user_type = forms.ChoiceField(
        choices=[("job_seeker", "Job Seeker"), ("recruiter", "Recruiter")],
        required=True,
        widget=forms.RadioSelect,
    )

    def signup(self, request: Any, user: User) -> User:
        """Save the user's signup data."""
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        user.user_type = cast(str, self.cleaned_data["user_type"])
        user.save(update_fields=["first_name", "last_name", "email", "user_type"])
        return user
