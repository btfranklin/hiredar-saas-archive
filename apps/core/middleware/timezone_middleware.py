"""Per-user timezone activation middleware.

If the authenticated user has the ``timezone`` attribute set (an IANA/Olson
string such as ``"America/Chicago"``), Django activates that timezone for the
lifetime of the request so all calls to ``timezone.localtime()`` and template
filters like ``{{ value|date }}`` render in the user's local zone.
"""

from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo

from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


class UserTimezoneMiddleware(MiddlewareMixin):
    """Activate the logged-in user's preferred timezone for each request."""

    def process_request(self, request):  # type: ignore[override]
        user: Any = getattr(request, "user", None)

        # 1. Detect browser-sent timezone via cookie (set by JS in base template)
        cookie_tz = request.COOKIES.get("tz")

        # Validate cookie string against the IANA database early so we don't
        # save garbage values to the database.
        def _is_valid_tz(name: str | None) -> bool:  # noqa: D401 – simple helper
            if not name:
                return False
            try:
                ZoneInfo(name)
                return True
            except Exception:
                return False

        cookie_is_valid = _is_valid_tz(cookie_tz)

        if getattr(user, "is_authenticated", False):
            active_tz = (
                cookie_tz if cookie_is_valid else getattr(user, "timezone", "UTC")
            )

            # Persist the cookie value if it is valid and differs from the DB value
            if cookie_is_valid and cookie_tz and cookie_tz != user.timezone:
                from django.contrib.auth import get_user_model

                UserModel = get_user_model()
                UserModel.objects.filter(pk=user.pk).update(timezone=cookie_tz)
                user.timezone = cookie_tz  # Reflect change in memory

            try:
                timezone.activate(active_tz)
            except Exception:
                timezone.deactivate()
        else:
            timezone.deactivate()
