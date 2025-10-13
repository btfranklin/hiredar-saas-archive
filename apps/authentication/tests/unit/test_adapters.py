"""Unit tests for SocialAccountAdapter pre_social_login behaviour."""

from typing import Any

import pytest
from allauth.account.models import EmailAddress
from allauth.core.exceptions import ImmediateHttpResponse
from django.http import HttpResponseRedirect
from django.test import RequestFactory
from django.urls import reverse

from apps.authentication.adapters import SocialAccountAdapter


class FakeQueryset:  # pylint: disable=too-few-public-methods
    """Minimal queryset stub returning a predetermined existence flag."""

    def __init__(self, exists: bool) -> None:
        self._exists = exists

    def exists(self) -> bool:
        """Return whether the fake queryset should pretend to have results."""
        return self._exists


class DummyUser:  # pylint: disable=too-few-public-methods
    """Simplified user stub so the adapter can mutate attributes."""

    def __init__(self, email: str) -> None:
        self.email = email
        self.user_type = "initial"
        self.name: str | None = None


class DummySocialLogin:  # pylint: disable=too-few-public-methods
    """Lightweight social login representation for the adapter tests."""

    def __init__(self, is_existing: bool, email: str) -> None:
        self.is_existing = is_existing
        self.user = DummyUser(email)


@pytest.mark.parametrize(
    "is_existing,email_exists,should_raise,expected_user_type",
    [
        (True, True, False, "initial"),
        (True, False, False, "initial"),
        (False, True, True, None),
        (False, False, False, "recruiter"),
    ],
)
def test_pre_social_login_combinatorics(
    monkeypatch: pytest.MonkeyPatch,
    is_existing: bool,
    email_exists: bool,
    should_raise: bool,
    expected_user_type: str | None,
) -> None:
    """Verify all combinations of pre_social_login branching paths."""
    adapter = SocialAccountAdapter()

    # Patch EmailAddress.objects.filter(...).exists()
    def fake_filter(**kwargs: Any) -> FakeQueryset:
        """Return a queryset stub that reports whether an email exists."""
        return FakeQueryset(email_exists)

    monkeypatch.setattr(EmailAddress.objects, "filter", fake_filter)

    sociallogin = DummySocialLogin(is_existing=is_existing, email="user@example.com")
    request = RequestFactory().get("/")

    if should_raise:
        with pytest.raises(ImmediateHttpResponse) as exc:
            adapter.pre_social_login(request, sociallogin)
        response = exc.value.response
        assert isinstance(response, HttpResponseRedirect)
        assert response.url == reverse("authentication:login")
    else:
        # Should not raise, and user_type should be correct
        adapter.pre_social_login(request, sociallogin)
        assert sociallogin.user.user_type == expected_user_type
