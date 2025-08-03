"""Tests for core app views."""

from django.test import TestCase
from django.urls import reverse


class CoreViewsTests(TestCase):
    """Test cases for core app views."""

    def test_home_page(self) -> None:
        """Test home page loads correctly."""
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")

    def test_healthcheck_endpoint(self) -> None:
        """Test healthcheck middleware returns '200 OK'."""
        response = self.client.get("/hc")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode().strip(), "200 OK")
