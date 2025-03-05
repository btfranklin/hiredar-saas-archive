from django.contrib.auth.models import User
from django.test import TestCase

from apps.recruiters.models import RecruiterProfile

from .models import JobOpening

# Create your tests here.


class JobOpeningModelTest(TestCase):
    def setUp(self):
        # Create a test user with recruiter profile
        self.test_user = User.objects.create_user(
            username="recruiter", email="recruiter@example.com", password="password123"
        )
        
        # Create a recruiter profile directly
        self.recruiter_profile = RecruiterProfile.objects.create(
            user=self.test_user,
            company_name="Test Company",
        )

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
        self.assertEqual(self.job_opening.recruiter.company_name, "Test Company")
        expected_str = f"Software Engineer at Test Company"
        self.assertEqual(str(self.job_opening), expected_str)

    def test_job_opening_skills(self):
        """Test that skills can be accessed through the required_skills_list property"""
        self.assertEqual(len(self.job_opening.required_skills_list), 3)
        self.assertIn("Python", self.job_opening.required_skills_list)
        self.assertIn("Django", self.job_opening.required_skills_list)
        self.assertIn("JavaScript", self.job_opening.required_skills_list)
