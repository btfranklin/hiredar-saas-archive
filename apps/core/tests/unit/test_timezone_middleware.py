"""Unit tests for UserTimezoneMiddleware.

These tests verify that the middleware
* activates the correct timezone for authenticated users
* persists a new cookie-provided zone back to the User model
* ignores cookies for anonymous users
* gracefully handles invalid timezone strings
* falls back to the stored user zone when no cookie is present
"""

from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.authentication.models import User
from apps.core.middleware.timezone_middleware import UserTimezoneMiddleware


class UserTimezoneMiddlewareTests(TestCase):
    """Test behavior of per-user timezone activation middleware."""

    def setUp(self) -> None:  # noqa: D401 – simple override
        self.factory = RequestFactory()
        # Provide a minimal no-op get_response callable
        self.middleware = UserTimezoneMiddleware(lambda request: HttpResponse())

    def tearDown(self) -> None:  # noqa: D401 – simple override
        # Ensure thread-local tz is reset between tests
        timezone.deactivate()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _process(self, request):  # type: ignore[no-self-use]
        """Run middleware and return the active tz name."""
        UserTimezoneMiddleware(lambda r: HttpResponse()).process_request(request)
        current = timezone.get_current_timezone_name()
        timezone.deactivate()
        return current

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_authenticated_cookie_updates_user(self):
        """Cookie should override DB value and update the user record."""
        user = User.objects.create_user(  # type: ignore[attr-defined]
            email="alice@example.com",
            password="passw0rd",
            user_type="job_seeker",
        )  # type: ignore[attr-defined]

        request = self.factory.get("/")
        request.COOKIES["tz"] = "America/Chicago"
        request.user = user  # type: ignore[attr-defined]

        tz_name = self._process(request)

        self.assertEqual(tz_name, "America/Chicago")
        user.refresh_from_db()
        self.assertEqual(user.timezone, "America/Chicago")

    def test_unauthenticated_cookie_ignored(self):
        """Anonymous visitors should not trigger tz activation from cookie."""
        anon = type("Anon", (), {"is_authenticated": False})()
        request = self.factory.get("/")
        request.COOKIES["tz"] = "America/Chicago"
        request.user = anon  # type: ignore

        tz_name = self._process(request)
        self.assertEqual(tz_name, settings.TIME_ZONE)

    def test_invalid_cookie_fallback_no_update(self):
        """Invalid tz string should fallback to default and not modify user."""
        user = User.objects.create_user(  # type: ignore[attr-defined]
            email="bob@example.com",
            password="passw0rd",
            user_type="job_seeker",
        )  # type: ignore[attr-defined]
        request = self.factory.get("/")
        request.COOKIES["tz"] = "Mars/Phobos"
        request.user = user  # type: ignore[attr-defined]

        tz_name = self._process(request)
        self.assertEqual(tz_name, settings.TIME_ZONE)
        user.refresh_from_db()
        self.assertEqual(user.timezone, "UTC")  # remains default

    def test_no_cookie_uses_user_timezone(self):
        """When no cookie is present, stored user.timezone wins."""
        user = User.objects.create_user(  # type: ignore[attr-defined]
            email="carol@example.com",
            password="passw0rd",
            user_type="job_seeker",
            timezone="Europe/Paris",
        )  # type: ignore[attr-defined]
        request = self.factory.get("/")
        request.user = user  # type: ignore[attr-defined]

        tz_name = self._process(request)
        self.assertEqual(tz_name, "Europe/Paris")
