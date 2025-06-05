import pytest
from allauth.account.models import EmailAddress
from allauth.core.exceptions import ImmediateHttpResponse
from django.http import HttpResponseRedirect
from django.test import RequestFactory
from django.urls import reverse

from apps.authentication.adapters import SocialAccountAdapter


class FakeQueryset:
    def __init__(self, exists):
        self._exists = exists

    def exists(self):
        return self._exists


class DummyUser:
    def __init__(self, email):
        self.email = email
        self.user_type = "initial"
        self.name = None


class DummySocialLogin:
    def __init__(self, is_existing, email):
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
    monkeypatch, is_existing, email_exists, should_raise, expected_user_type
):
    adapter = SocialAccountAdapter()

    # Patch EmailAddress.objects.filter(...).exists()
    def fake_filter(**kwargs):
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
