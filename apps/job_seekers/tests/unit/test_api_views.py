from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from apps.authentication.models import User
from apps.job_seekers.models import JobSeekerProfile, RoleRecommendation


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
