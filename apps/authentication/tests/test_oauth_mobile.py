import json
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.authentication.models import User as AuthUser


class LinkedInMobileViewsTest(TestCase):
    def test_linkedin_mobile_redirect_view(self):
        url = reverse("linkedin_mobile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Ensure the redirect stub deep-links to the custom scheme
        self.assertContains(
            response, 'window.location = "hiredar://oauth?" + location.search'
        )

    def test_linkedin_mobile_finish_view(self):
        url = reverse("linkedin_mobile_finish")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Ensure the finish stub calls the correct API endpoint
        self.assertContains(response, "fetch('/api/auth/linkedin/mobile-finish'")


class LinkedInMobileFinishAPITest(TestCase):
    def setUp(self):
        self.url = reverse("linkedin_mobile_finish_api")
        # Override settings for test
        settings.LI_CLIENT_ID = "dummy_id"
        settings.LI_CLIENT_SECRET = "dummy_secret"
        settings.LI_MOBILE_REDIRECT = "https://hiredar.com/linkedin-mobile/"

    @patch("apps.authentication.views.oauth_mobile.requests.post")
    @patch("apps.authentication.views.oauth_mobile.requests.get")
    def test_successful_finish(self, mock_get, mock_post):
        # Mock access token response
        mock_response_token = MagicMock()
        mock_response_token.raise_for_status.return_value = None
        mock_response_token.json.return_value = {"access_token": "test_token"}
        mock_post.return_value = mock_response_token

        # Mock profile and email responses
        def mock_get_side_effect(url, headers, timeout):
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            if "v2/me" in url:
                mock_resp.json.return_value = {
                    "localizedFirstName": "Jane",
                    "localizedLastName": "Doe",
                }
            else:
                mock_resp.json.return_value = {
                    "elements": [{"handle~": {"emailAddress": "jane@example.com"}}]
                }
            return mock_resp

        mock_get.side_effect = mock_get_side_effect

        payload = {
            "code": "abc123",
            "code_verifier": "verifier",
            "user_type": "job_seeker",
        }
        response = self.client.post(
            self.url, data=json.dumps(payload), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

        # Verify user was created and named correctly
        user = AuthUser.objects.get(email="jane@example.com")
        self.assertEqual(user.name, "Jane Doe")
