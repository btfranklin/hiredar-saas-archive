from urllib.parse import parse_qs, urlparse

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_linkedin_oidc_redirect(client):
    url = reverse("openid_connect_login", kwargs={"provider_id": "linkedin"})
    response = client.get(url)
    assert response.status_code == 302
    loc = response["Location"]
    assert "linkedin.com/oauth/v2/authorization" in loc
    assert "response_type=code" in loc
    # Verify that OIDC scopes include exactly openid, profile, and email, regardless of order or encoding
    parts = urlparse(loc)
    qs = parse_qs(parts.query)
    assert "scope" in qs
    values = qs["scope"][0].split()
    assert set(values) == {"openid", "profile", "email"}
