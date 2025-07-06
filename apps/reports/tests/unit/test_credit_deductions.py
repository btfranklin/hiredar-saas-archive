from __future__ import annotations

from django.test import Client, TestCase
from django.urls import reverse

from apps.authentication.models import User
from apps.recruiters.models import JobOpening, RecruiterProfile


class ShortlistExportCreditsTests(TestCase):
    """Verify that exporting shortlists deducts credits and handles insufficiency."""

    def setUp(self):  # noqa: D401 – tests
        # Recruiter with plenty of credits
        self.user = User.objects.create_user(  # type: ignore[attr-defined]
            email="rec@example.com", password="pass", user_type="recruiter"
        )
        self.profile: RecruiterProfile = RecruiterProfile.objects.get(user=self.user)
        self.job_opening = JobOpening.objects.create(
            recruiter=self.profile,
            title="Test Job",
            description="Desc",
        )

        self.client = Client()
        self.client.login(email="rec@example.com", password="pass")

    # ------------------------------------------------------------------
    # Successful export – credits deducted
    # ------------------------------------------------------------------

    def test_export_csv_deducts_credits(self):
        starting_credits = self.profile.credits_available
        url = reverse("reports:export_csv", args=[self.job_opening.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.credits_available, starting_credits - 5)
        self.assertEqual(self.profile.total_shortlist_csvs_generated, 1)

    def test_export_pdf_deducts_credits(self):
        starting_credits = self.profile.credits_available
        url = reverse("reports:export_pdf", args=[self.job_opening.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.credits_available, starting_credits - 5)
        self.assertEqual(self.profile.total_shortlist_pdfs_generated, 1)

    # ------------------------------------------------------------------
    # Insufficient credits – 400 response and no deduction
    # ------------------------------------------------------------------

    def test_export_csv_insufficient_credits(self):
        # Reduce credits below threshold
        self.profile.credits_available = 3
        self.profile.save(update_fields=["credits_available"])

        url = reverse("reports:export_csv", args=[self.job_opening.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        # Credits unchanged
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.credits_available, 3)
        self.assertEqual(self.profile.total_shortlist_csvs_generated, 0)

    def test_export_pdf_insufficient_credits(self):
        self.profile.credits_available = 2
        self.profile.save(update_fields=["credits_available"])

        url = reverse("reports:export_pdf", args=[self.job_opening.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.credits_available, 2)
        self.assertEqual(self.profile.total_shortlist_pdfs_generated, 0)
