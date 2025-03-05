"""Type definitions for the authentication app."""

from typing import TYPE_CHECKING, ClassVar, Literal, TypedDict

from django.contrib.auth.models import AbstractBaseUser

if TYPE_CHECKING:
    from apps.authentication.models import User, UserManager
    from apps.job_seekers.models import JobSeekerProfile
    from apps.recruiters.models import RecruiterProfile


class UserType(TypedDict):
    """Type definition for user data."""

    email: str
    first_name: str
    last_name: str
    user_type: Literal["job_seeker", "recruiter"]
    bio: str | None
    location: str | None


class AuthenticatedUser(AbstractBaseUser):
    """Type definition for an authenticated user."""

    email: str
    first_name: str
    last_name: str
    user_type: Literal["job_seeker", "recruiter"]
    bio: str | None
    location: str | None
    job_seeker_profile: "JobSeekerProfile | None"
    recruiter_profile: "RecruiterProfile | None"
    is_staff: bool
    is_active: bool
    is_superuser: bool
    objects: ClassVar["UserManager[User]"]
