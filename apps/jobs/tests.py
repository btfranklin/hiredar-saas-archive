from django.test import TestCase

from apps.authentication.models import User
from apps.recruiters.models import RecruiterProfile

from .models import JobOpening

# Create your tests here.


class JobOpeningModelTest(TestCase):
    def setUp(self):
        # Create a test user with recruiter profile - the profile will be created automatically by the signal
        self.test_user = User.objects.create_user(  # type: ignore
            email="recruiter@example.com",
            password="password123",
            user_type="recruiter",
            first_name="Test",
            last_name="Recruiter",
        )

        # Get the automatically created recruiter profile
        self.recruiter_profile = RecruiterProfile.objects.get(user=self.test_user)

        # Create a job opening
        self.job_opening = JobOpening.objects.create(
            title="Software Engineer",
            recruiter=self.recruiter_profile,
            description="Test description",
            location="Remote",
            required_skills="Python, Django, JavaScript",
            experience_years=3,
            is_active=True,
        )

    def test_job_opening_creation(self):
        """Test that job opening can be created"""
        self.assertEqual(self.job_opening.title, "Software Engineer")
        # Test the string representation format which is "{title} - {company}"
        expected_str = f"Software Engineer - "
        self.assertEqual(str(self.job_opening), expected_str)

    def test_job_opening_skills(self):
        """Test that skills can be accessed through the required_skills_list property"""
        self.assertEqual(len(self.job_opening.required_skills_list), 3)
        self.assertIn("Python", self.job_opening.required_skills_list)
        self.assertIn("Django", self.job_opening.required_skills_list)
        self.assertIn("JavaScript", self.job_opening.required_skills_list)
