"""
Tests for the PageViewCountMiddleware.
"""

from __future__ import annotations

from django.test import TestCase
from django.urls import reverse

from apps.core.models import PageViewCount


class TestPageViewCountMiddleware(TestCase):
    def test_increments_get_requests(self) -> None:
        url = reverse("core:test")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        entry = PageViewCount.objects.get(path=url)
        self.assertEqual(entry.view_count, 1)
        self.assertIsNotNone(entry.last_viewed_at)

        self.client.get(url)
        entry.refresh_from_db()
        self.assertEqual(entry.view_count, 2)

    def test_ignores_non_get_requests(self) -> None:
        url = reverse("core:test")

        self.client.get(url)
        self.client.post(url)

        entry = PageViewCount.objects.get(path=url)
        self.assertEqual(entry.view_count, 1)

    def test_ignores_error_responses(self) -> None:
        url = "/does-not-exist/"

        self.client.get(url)

        self.assertFalse(PageViewCount.objects.filter(path=url).exists())

    def test_tracks_signup_page(self) -> None:
        url = reverse("authentication:signup")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        entry = PageViewCount.objects.get(path=url)
        self.assertEqual(entry.view_count, 1)

    def test_ignores_non_core_auth_pages(self) -> None:
        url = reverse("authentication:login")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertFalse(PageViewCount.objects.filter(path=url).exists())
