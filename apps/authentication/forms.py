"""Forms for user authentication and registration."""

from typing import Any, cast

from allauth.account.forms import SignupForm as AllAuthSignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserChangeForm,
    UserCreationForm,
)
from django.http import HttpRequest

from apps.authentication.models import User


class CustomUserCreationForm(UserCreationForm):
    """Form for creating new users."""

    class Meta:
        """Meta class for CustomUserCreationForm."""

        model = User
        fields = ("email", "name", "user_type")

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
        fields = ("email", "name")


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


class CustomSignupForm(forms.Form):
    """Form for user signup."""

    name = forms.CharField(max_length=255, required=False)
    email = forms.EmailField(required=True)
    user_type = forms.ChoiceField(
        choices=[("job_seeker", "Job Seeker"), ("recruiter", "Recruiter")],
        required=True,
        widget=forms.RadioSelect,
    )

    def signup(self, request: Any, user: User) -> User:
        """Save the user's signup data."""
        if self.cleaned_data.get("name"):
            user.name = self.cleaned_data["name"]
        user.email = self.cleaned_data["email"]
        user.user_type = cast(str, self.cleaned_data["user_type"])
        user.save(update_fields=["name", "email", "user_type"])
        return user


class JobSeekerSignupForm(AllAuthSignupForm):
    """
    Custom signup form for job seekers.

    This form extends allauth's SignupForm to support job seeker-specific behavior.
    """

    us_only_certification = forms.BooleanField(
        required=True,
        label=(
            "I confirm that I am physically located in the United States and will "
            "use Hiredar exclusively for US-based employment purposes."
        ),
    )

    def save(self, request: HttpRequest) -> User:
        """Save the user with job seeker user type."""
        # First save the user using allauth's parent method
        user = super().save(request)  # type: ignore
        assert isinstance(user, User), "Expected a User instance"

        # Set job seeker specific fields
        user.user_type = "job_seeker"
        user.name = "New User"  # Default name until resume is parsed

        # Mark the user as having certified US-only usage
        user.is_us_certified = True
        user.save()

        return user


class RecruiterSignupForm(AllAuthSignupForm):
    """
    Custom signup form for recruiters.

    This form extends allauth's SignupForm to support recruiter-specific behavior,
    including requiring a name field.
    """

    # Add name field which is required for recruiters
    name = forms.CharField(
        max_length=150,
        label="Full Name",
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Your name"}),
    )

    us_only_certification = forms.BooleanField(
        required=True,
        label=(
            "I confirm that I am physically located in the United States and will "
            "use Hiredar exclusively for US-based recruiting activities."
        ),
    )

    def clean_name(self):
        """Validate that name is provided."""
        name = self.cleaned_data.get("name", "").strip()
        if not name or name == "New User":
            raise forms.ValidationError("Please provide your name")
        return name

    def save(self, request: HttpRequest) -> User:
        """Save the user with recruiter user type and name."""
        # First save the user using allauth's parent method
        user = super().save(request)  # type: ignore
        assert isinstance(user, User), "Expected a User instance"

        # Set recruiter specific fields
        user.user_type = "recruiter"
        user.name = self.cleaned_data.get("name")

        # Mark the user as having certified US-only usage
        user.is_us_certified = True
        user.save()

        return user


class SocialAccountSignupForm(SocialSignupForm):
    """
    Custom form for social account signup.

    This form extends allauth's SocialSignupForm to capture additional fields
    and set the appropriate user type during social registration.
    """

    name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Your full name"}),
    )

    user_type = forms.ChoiceField(
        choices=[
            ("job_seeker", "Job Seeker"),
            ("recruiter", "Recruiter"),
        ],
        widget=forms.RadioSelect,
        initial="job_seeker",
    )

    us_only_certification = forms.BooleanField(
        required=True,
        label=(
            "I confirm that I am physically located in the United States and will "
            "use Hiredar exclusively for US-based employment or recruiting purposes."
        ),
    )

    def save(self, request):
        """Save the user with the appropriate user type and other details."""
        user = super().save(request)

        # Set user type
        user_type = self.cleaned_data.get("user_type", "job_seeker")
        user.user_type = user_type

        # Set name if provided
        if self.cleaned_data.get("name"):
            user.name = self.cleaned_data["name"]

        # Mark the user as having certified US-only usage
        user.is_us_certified = True

        # Save user
        user.save()

        return user
