from __future__ import annotations

from unittest.mock import patch

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse

from apps.authentication.models import User
from apps.job_seekers.models import JobSeekerProfile, RoleRecommendation
from apps.job_seekers.services.recommendation import llm_processor


@pytest.mark.django_db
class TestToggleRoleInterestView:
    """Unit tests for the ToggleRoleInterestView API endpoint."""

    def _setup_user_with_roles(
        self,
    ) -> tuple[User, JobSeekerProfile, RoleRecommendation, RoleRecommendation]:
        """Create a job-seeker user, profile and two role recommendations."""

        user = User.objects.create_user(  # type: ignore[arg-type]
            email="js@example.com",
            password="pass1234",
            user_type="job_seeker",
            name="Jane Seeker",
        )

        # Fetch the profile automatically created by the signal and attach
        # a dummy resume so the resume-upload middleware passes.
        profile = JobSeekerProfile.objects.get(user_owner=user)
        profile.resume_xml = "<resume />"
        profile.save(update_fields=["resume_xml"])

        role_1 = RoleRecommendation.objects.create(
            job_seeker=profile,
            role_title="Backend Engineer",
            description="Build APIs",
            is_candidate_interested=False,
        )
        role_2 = RoleRecommendation.objects.create(
            job_seeker=profile,
            role_title="Data Engineer",
            description="Manage data pipelines",
            is_candidate_interested=True,
        )

        return user, profile, role_1, role_2

    def test_htmx_toggle_updates_interest_and_returns_partial(self):
        """HTMX request toggles interest and returns updated HTML partial."""

        user, _profile, role, _ = self._setup_user_with_roles()
        client = Client()
        client.force_login(user)

        url = reverse("job_seekers:toggle_role_interest", args=[role.pk])

        response = client.post(
            url,
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="recommended-roles-section",
        )

        assert response.status_code == 200

        # Role should now be marked as interested
        role.refresh_from_db()
        assert role.is_candidate_interested is True

        # Returned HTML should contain the wrapper div for the card
        assert b'id="recommended-roles-section"' in response.content

    def test_json_toggle_updates_interest_and_returns_json(self):
        """Non-HTMX request returns JSON payload and toggles interest."""

        user, _profile, role, _ = self._setup_user_with_roles()
        client = Client()
        client.force_login(user)

        url = reverse("job_seekers:toggle_role_interest", args=[role.pk])

        response = client.post(url)

        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["role_id"] == role.pk
        assert payload["is_interested"] is True

        # Confirm persistence
        role.refresh_from_db()
        assert role.is_candidate_interested is True


@pytest.mark.django_db
def test_role_recommendations_reasoning_effort_setting():
    # Arrange a fake client that records arguments to Responses API
    class _FakeResponse:
        def __init__(self):
            self.output_text = "<role_recommendations></role_recommendations>"

    class _Responses:
        def __init__(self, outer):
            self._outer = outer

        def create(self, **kwargs):
            self._outer.called_with = kwargs
            return _FakeResponse()

    class _FakeClient:
        def __init__(self):
            self.called_with = None
            self.responses = _Responses(self)

        def with_options(self, **_):
            return self

    # Create minimal profile with resume_xml so generation runs
    user = User.objects.create_user(  # type: ignore[arg-type]
        email="js2@example.com",
        password="pass1234",
        user_type="job_seeker",
        name="Jane Seeker 2",
    )
    profile = JobSeekerProfile.objects.get(user_owner=user)
    profile.resume_xml = "<resume />"
    profile.save(update_fields=["resume_xml"])

    fake = _FakeClient()
    with patch("hiredar.llm.client.get_client", return_value=fake):
        _ = llm_processor.generate_role_recommendations(profile.resume_xml)

    # Assert reasoning was forwarded with the configured key name
    assert fake.called_with is not None
    reasoning = fake.called_with.get("reasoning", {})
    assert (
        reasoning.get("effort")
        == settings.JOBSEEKERS_ROLE_RECOMMENDATION_REASONING_EFFORT
    )
