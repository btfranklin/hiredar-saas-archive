"""Type definitions for the authentication app."""

import sys
from typing import Any, Literal, Protocol, TypedDict

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


class UserType(TypedDict):
    """Type definition for user data."""

    email: str
    name: str
    user_type: Literal["job_seeker", "recruiter"]


class AuthenticatedUser(Protocol):
    """A protocol for the authenticated user type."""

    pk: int
    email: str
    name: str
    user_type: Literal["job_seeker", "recruiter", "admin"]
    is_job_seeker: bool
    is_recruiter: bool
    is_admin: bool
    is_staff: bool
    is_authenticated: bool

    # Relationships managed by related managers
    # These are not directly on the User model but are included here for type checking
    job_seeker_profile: Any
    recruiter_profile: Any

    def get_initials(self) -> str:
        """Get user initials for avatar display."""
        raise NotImplementedError("get_initials must be implemented")

    def to_dict(self) -> dict[str, Any]:
        """Convert user instance to a dictionary."""
        raise NotImplementedError("to_dict must be implemented")

    # Class methods
    @classmethod
    def get_job_seekers(cls: type[Self]) -> Any:
        """Get all job seekers."""
        raise NotImplementedError("get_job_seekers must be implemented")

    @classmethod
    def get_recruiters(cls: type[Self]) -> Any:
        """Get all recruiters."""
        raise NotImplementedError("get_recruiters must be implemented")

    @classmethod
    def get_admins(cls: type[Self]) -> Any:
        """Get all admins."""
        raise NotImplementedError("get_admins must be implemented")
