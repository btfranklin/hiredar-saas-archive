from django.test import Client, TestCase
from django.urls import reverse

from apps.authentication.models import User
from apps.candidates.models import CandidatePool, CandidateProfile
from apps.matching.models import CandidateMatch, ShortlistedMatch
from apps.recruiters.models import JobOpening, RecruiterProfile


class ShortlistCountersTests(TestCase):
    """Test that recruiter profile shortlist counters update correctly."""

    def setUp(self):
        # Create recruiter and profile
        self.recruiter_user = User.objects.create_user(email="rec@example.com", password="pass", user_type="recruiter")  # type: ignore[attr-defined]
        # RecruiterProfile is auto-created by signal on user creation; fetch it
        self.recruiter_profile = RecruiterProfile.objects.get(user=self.recruiter_user)
        # Create job opening
        self.job_opening = JobOpening.objects.create(
            recruiter=self.recruiter_profile,
            title="Test Job",
            description="Test description",
        )
        # Create pool-owned candidate profile
        candidate_pool = CandidatePool.objects.create(
            recruiter=self.recruiter_user, name="Shortlist Pool"
        )
        self.candidate_profile = CandidateProfile.objects.create(
            pool=candidate_pool,
            candidate_name="Shortlist Candidate",
            promotional_blurb="",
            experience_overview="",
            skills="Python\nDjango",
            is_published=True,
        )
        self.candidate_match = CandidateMatch.objects.create(
            job_opening=self.job_opening,
            candidate_profile=self.candidate_profile,
        )
        # Authenticate client
        self.client = Client()
        self.client.login(email="rec@example.com", password="pass")

    def test_add_and_remove_shortlist_updates_counter(self):
        # Initial counter should be zero
        self.assertEqual(self.recruiter_profile.total_candidates_shortlisted, 0)
        # Add to shortlist
        url_add = reverse(
            "matching:add_to_shortlist",
            args=[self.job_opening.pk, self.candidate_profile.pk],
        )
        response_add = self.client.post(url_add)
        self.assertEqual(response_add.status_code, 200)
        self.recruiter_profile.refresh_from_db()
        self.assertEqual(self.recruiter_profile.total_candidates_shortlisted, 1)
        # Verify shortlist entry exists
        shortlist = ShortlistedMatch.objects.get(
            job_opening=self.job_opening,
            candidate_match=self.candidate_match,
        )
        # Remove from shortlist
        url_remove = reverse(
            "matching:remove_from_shortlist",
            args=[self.job_opening.pk, shortlist.pk],
        )
        response_remove = self.client.post(url_remove)
        self.assertEqual(response_remove.status_code, 200)
        self.recruiter_profile.refresh_from_db()
        self.assertEqual(self.recruiter_profile.total_candidates_shortlisted, 0)
