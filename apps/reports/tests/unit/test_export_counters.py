"""Ensure export actions increment recruiter counters correctly."""

# pylint: disable=missing-function-docstring

from django.test import Client, TestCase
from django.urls import reverse

from apps.authentication.models import User
from apps.candidates.models import CandidatePool
from apps.job_seekers.models import JobSeekerProfile, TalentSheet
from apps.matching.models import CandidateMatch, ShortlistedMatch
from apps.recruiters.models import JobOpening, RecruiterProfile


class ExportCountersTests(TestCase):
    """Test that export CSV/PDF increments recruiter profile counters."""

    def setUp(self):
        # Create recruiter and profile
        self.rec_user = User.objects.create_user(email="rec2@example.com", password="pass", user_type="recruiter")  # type: ignore[attr-defined]
        # RecruiterProfile is auto-created by signal on user creation; fetch it
        self.profile = RecruiterProfile.objects.get(user=self.rec_user)
        # Create job opening
        self.job_opening = JobOpening.objects.create(
            recruiter=self.profile,
            title="Reporting Job",
            description="Description for reports",
        )
        # Create a pool-owned candidate profile and shortlist entry
        candidate_pool = CandidatePool.objects.create(
            recruiter=self.rec_user, name="Reporting Pool"
        )
        job_seeker_profile = JobSeekerProfile.objects.create(
            candidate_pool=candidate_pool,
            candidate_name="Reporting Candidate",
            most_recent_title="Data Analyst",
        )
        talent_sheet = TalentSheet.objects.create(
            job_seeker=job_seeker_profile,
            promotional_blurb="",
            experience_overview="",
            ideal_roles="",
            skills="",
            personal_tagline="",
            is_published=False,
            qualifications="",
        )
        candidate_match = CandidateMatch.objects.create(
            job_opening=self.job_opening,
            talent_sheet=talent_sheet,
        )
        ShortlistedMatch.objects.create(
            job_opening=self.job_opening,
            candidate_match=candidate_match,
        )
        # Authenticate client
        self.client = Client()
        self.client.login(email="rec2@example.com", password="pass")

    def test_export_csv_increments_counter(self):
        # Counter starts at zero
        self.assertEqual(self.profile.total_shortlist_csvs_generated, 0)
        # Call export CSV view
        url = reverse("reports:export_csv", args=[self.job_opening.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Counter should increment
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.total_shortlist_csvs_generated, 1)

    def test_export_pdf_increments_counter(self):
        # Counter starts at zero
        self.assertEqual(self.profile.total_shortlist_pdfs_generated, 0)
        # Call export PDF view
        url = reverse("reports:export_pdf", args=[self.job_opening.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Counter should increment
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.total_shortlist_pdfs_generated, 1)
