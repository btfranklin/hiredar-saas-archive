"""
Unit tests for the reports app services.

Tests the CSV and PDF generation functionality for shortlisted candidates.
"""

from unittest.mock import patch

from django.test import TestCase

from apps.authentication.models import User
from apps.candidates.models import CandidatePool, CandidateProfile
from apps.matching.models import CandidateMatch, ShortlistedMatch
from apps.recruiters.models import JobOpening, RecruiterProfile
from apps.reports.services import generate_csv, generate_pdf, get_export_filename


class ReportsServiceTests(TestCase):
    """Test the reports service functions."""

    @classmethod
    def setUpTestData(cls):
        """Set up shared test data once for the entire test case."""
        # Create recruiter
        cls.recruiter_user = User.objects.create_user(
            email="recruiter@test.com",
            password="testpass123",
            user_type="recruiter",
            name="Test Recruiter",
        )
        cls.recruiter_profile, _ = RecruiterProfile.objects.get_or_create(
            user=cls.recruiter_user
        )

        # Create job opening
        cls.job_opening = JobOpening.objects.create(
            recruiter=cls.recruiter_profile,
            title="Senior Python Developer",
            description="Looking for a senior Python developer",
            required_skills="Python\nDjango\nPostgreSQL",
            status="active",
        )

        # Create pool-owned candidate profile representing an ingested resume
        cls.candidate_pool = CandidatePool.objects.create(
            recruiter=cls.recruiter_user,
            name="Primary Pool",
        )
        cls.candidate_profile = CandidateProfile.objects.create(
            pool=cls.candidate_pool,
            candidate_name="Test Candidate",
            most_recent_title="Python Developer",
            location="San Francisco, CA",
            years_of_experience=5,
            phone="555-123-4567",
            promotional_blurb="Experienced Python developer with Django expertise",
            experience_overview="5 years of Python development experience",
            skills="Python\nDjango\nPostgreSQL\nReact",
            personal_tagline="Full-stack Python developer",
            is_published=True,
        )

        # Ensure a candidate match exists (background tasks may create one already).
        cls.candidate_match, _ = CandidateMatch.objects.update_or_create(
            job_opening=cls.job_opening,
            candidate_profile=cls.candidate_profile,
            defaults={
                "holistic_score": 0.85,
                "skills_score": 0.90,
                "experience_score": 0.80,
                "qualifications_score": 0.75,
                "wildcard_score": 0.70,
                "match_summary": "Strong Python and Django skills",
            },
        )

        # Create shortlisted match
        cls.shortlisted_match = ShortlistedMatch.objects.create(
            job_opening=cls.job_opening, candidate_match=cls.candidate_match
        )

    def test_generate_csv_with_shortlisted_candidates(self):
        """Test CSV generation includes shortlisted candidates."""
        csv_data = generate_csv(self.job_opening)
        csv_string = csv_data.decode("utf-8")

        # Check header is present
        self.assertIn("candidate_id", csv_string)
        self.assertIn("full_name", csv_string)
        self.assertIn("match_score_overall", csv_string)

        # Check candidate data is present (pool-owned candidates use candidate_name)
        self.assertIn("Test Candidate", csv_string)
        self.assertIn("85.0%", csv_string)  # holistic score
        self.assertIn("Python, Django, PostgreSQL, React", csv_string)  # skills
        # Note: phone and title might be empty due to get_or_create defaults

    def test_generate_csv_with_limit(self):
        """Test CSV generation respects limit parameter."""
        # Create another shortlisted candidate
        candidate_profile_2 = CandidateProfile.objects.create(
            pool=self.candidate_pool,
            candidate_name="Second Candidate",
            most_recent_title="Senior Developer",
            promotional_blurb="Another great candidate",
            experience_overview="Lots of experience",
            is_published=True,
        )
        match_2, _ = CandidateMatch.objects.update_or_create(
            job_opening=self.job_opening,
            candidate_profile=candidate_profile_2,
            defaults={
                "holistic_score": 0.75,
            },
        )
        ShortlistedMatch.objects.create(
            job_opening=self.job_opening, candidate_match=match_2
        )

        # Generate CSV with limit of 1
        csv_data = generate_csv(self.job_opening, limit=1)
        csv_string = csv_data.decode("utf-8")

        # Should only have 2 lines (header + 1 candidate)
        lines = csv_string.strip().split("\n")
        self.assertEqual(len(lines), 2)

    @patch("apps.reports.services.HTML")
    def test_generate_pdf_with_shortlisted_candidates(self, mock_html):
        """Test PDF generation includes shortlisted candidates."""
        mock_html.return_value.write_pdf.return_value = b"%PDF-FAKE"

        pdf_data = generate_pdf(self.job_opening)

        # Check that PDF data is generated
        self.assertIsInstance(pdf_data, bytes)
        self.assertGreater(len(pdf_data), 0)

        # PDF should start with PDF header
        self.assertTrue(pdf_data.startswith(b"%PDF"))
        mock_html.assert_called_once()
        mock_html.return_value.write_pdf.assert_called_once_with()

    def test_get_export_filename(self):
        """Test filename generation."""
        csv_filename = get_export_filename(self.job_opening, "csv")
        pdf_filename = get_export_filename(self.job_opening, "pdf")

        self.assertIn("Senior_Python_Developer", csv_filename)
        self.assertIn(".csv", csv_filename)
        self.assertIn("hiredar_candidates_", csv_filename)

        self.assertIn("Senior_Python_Developer", pdf_filename)
        self.assertIn(".pdf", pdf_filename)
        self.assertIn("hiredar_candidates_", pdf_filename)

    def test_generate_csv_empty_shortlist(self):
        """Test CSV generation with no shortlisted candidates."""
        # Remove the shortlisted match
        self.shortlisted_match.delete()

        csv_data = generate_csv(self.job_opening)
        csv_string = csv_data.decode("utf-8")

        # Should only have header row
        lines = csv_string.strip().split("\n")
        self.assertEqual(len(lines), 1)
        self.assertIn("candidate_id", lines[0])

    def test_generate_csv_with_pool_owned_candidate(self):
        """Test CSV generation uses candidate_name for pool-owned candidates."""
        # Create a recruiter for the pool
        pool_recruiter_user = User.objects.create_user(
            email="poolrecruiter@test.com",
            password="testpass123",
            user_type="recruiter",
            name="Pool Recruiter",
        )
        _pool_recruiter_profile, _ = RecruiterProfile.objects.get_or_create(
            user=pool_recruiter_user
        )

        candidate_pool = CandidatePool.objects.create(
            recruiter=pool_recruiter_user,  # Use the User, not the Profile
            name="Test Pool",
        )

        # Create a pool-owned candidate profile with candidate_name
        pool_candidate = CandidateProfile.objects.create(
            pool=candidate_pool,
            candidate_name="Jane Smith",  # This should be used in the report
            most_recent_title="Software Engineer",
            promotional_blurb="Pool candidate with parsed name",
            is_published=True,
        )

        match_pool, _ = CandidateMatch.objects.update_or_create(
            job_opening=self.job_opening,
            candidate_profile=pool_candidate,
            defaults={
                "holistic_score": 0.75,
            },
        )
        ShortlistedMatch.objects.create(
            job_opening=self.job_opening, candidate_match=match_pool
        )

        csv_data = generate_csv(self.job_opening)
        csv_string = csv_data.decode("utf-8")

        # Should use the parsed candidate_name
        self.assertIn("Jane Smith", csv_string)
        self.assertNotIn(
            "Candidate ", csv_string
        )  # Should not fall back to generic name
