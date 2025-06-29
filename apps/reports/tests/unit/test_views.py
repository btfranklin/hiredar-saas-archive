"""
Unit tests for the reports app views.

Tests the CSV and PDF export views.
"""

from django.test import TestCase
from django.urls import reverse

from apps.authentication.models import User
from apps.recruiters.models import JobOpening, RecruiterProfile


class ReportsViewTests(TestCase):
    """Test the reports views."""

    def setUp(self):
        """Set up test data."""
        # Create recruiter
        self.recruiter_user = User.objects.create_user(
            email="recruiter@test.com",
            password="testpass123",
            user_type="recruiter",
            name="Test Recruiter",
        )
        self.recruiter_profile, _ = RecruiterProfile.objects.get_or_create(
            user=self.recruiter_user
        )

        # Create job opening
        self.job_opening = JobOpening.objects.create(
            recruiter=self.recruiter_profile,
            title="Test Job",
            description="Test description",
            status="active",
        )

    def test_export_csv_requires_login(self):
        """Test that CSV export requires login."""
        url = reverse("reports:export_csv", kwargs={"job_id": self.job_opening.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_export_pdf_requires_login(self):
        """Test that PDF export requires login."""
        url = reverse("reports:export_pdf", kwargs={"job_id": self.job_opening.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_export_csv_success(self):
        """Test successful CSV export."""
        self.client.force_login(self.recruiter_user)
        url = reverse("reports:export_csv", kwargs={"job_id": self.job_opening.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_export_pdf_success(self):
        """Test successful PDF export."""
        self.client.force_login(self.recruiter_user)
        url = reverse("reports:export_pdf", kwargs={"job_id": self.job_opening.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_export_csv_wrong_recruiter(self):
        """Test that recruiters can only export their own job openings."""
        # Create another recruiter
        other_recruiter = User.objects.create_user(
            email="other@test.com",
            password="testpass123",
            user_type="recruiter",
            name="Other Recruiter",
        )

        self.client.force_login(other_recruiter)
        url = reverse("reports:export_csv", kwargs={"job_id": self.job_opening.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)  # Job not found for this recruiter
