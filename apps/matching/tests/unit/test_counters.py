from django.test import Client, TestCase
from django.urls import reverse

from apps.authentication.models import User
from apps.candidates.models import CandidatePool
from apps.job_seekers.models import JobSeekerProfile, TalentSheet
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
        # Create job seeker and talent sheet
        self.seeker_user = User.objects.create_user(email="seeker@example.com", password="pass", user_type="job_seeker")  # type: ignore[attr-defined]
        self.job_seeker_profile = JobSeekerProfile.objects.create(
            user_owner=self.seeker_user
        )
        self.talent_sheet = TalentSheet.objects.create(
            job_seeker=self.job_seeker_profile,
            promotional_blurb="",
            experience_overview="",
            ideal_roles="",
            skills="",
            personal_tagline="",
            salary_min=None,
            is_published=False,
            qualifications="",
        )
        self.candidate_match = CandidateMatch.objects.create(
            job_opening=self.job_opening,
            talent_sheet=self.talent_sheet,
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
            args=[self.job_opening.pk, self.job_seeker_profile.pk],
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
