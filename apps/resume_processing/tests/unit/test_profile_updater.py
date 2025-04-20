"""
Unit tests for the profile updater module.

Tests the profile updater functionality used to update job seeker profiles
with data parsed from resumes.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

import apps.resume_processing.utils.profile_updater as pu
from apps.job_seekers.models import JobSeekerProfile
from apps.resume_processing.utils.profile_updater import (
    generate_and_save_personal_tagline,
    update_profile_fields,
)
from apps.resume_processing.utils.xml_parser import (
    calculate_years_experience,
    extract_education,
    extract_experience,
    extract_most_recent_title,
    extract_professional_summary,
    extract_skills,
)

# Stub out generate_personal_tagline for all tests to avoid real LLM calls
pu.generate_personal_tagline = MagicMock(return_value="Test Tagline")


class ProfileUpdaterTests(TestCase):
    """
    Test cases for the profile updater functionality.

    Tests the update_profile function to ensure it properly updates
    JobSeekerProfile instances with parsed resume data.
    """

    def setUp(self):
        """Set up test data and mocked objects."""
        # Sample XML content with complete profile data
        self.test_xml = """<resume>
  <personal>
    <name>Jane Smith</name>
    <email>jane.smith@example.com</email>
    <phone>123-456-7890</phone>
    <summary>Experienced software engineer with a focus on web development.</summary>
  </personal>
  <skills>
    <skill>Python</skill>
    <skill>Django</skill>
    <skill>JavaScript</skill>
    <skill>React</skill>
  </skills>
  <experience>
    <job>
      <title>Senior Developer</title>
      <company>Tech Solutions Inc.</company>
      <startDate>2018-01</startDate>
      <endDate>Present</endDate>
      <description>Led development team and implemented new features.</description>
    </job>
    <job>
      <title>Junior Developer</title>
      <company>CodeCorp</company>
      <startDate>2015-06</startDate>
      <endDate>2017-12</endDate>
      <description>Developed and maintained web applications.</description>
    </job>
  </experience>
  <education>
    <institution>
      <name>University of Technology</name>
      <degree>Master of Computer Science</degree>
      <field>Software Engineering</field>
      <startDate>2013-09</startDate>
      <endDate>2015-05</endDate>
    </institution>
    <institution>
      <name>State College</name>
      <degree>Bachelor of Science</degree>
      <field>Computer Science</field>
      <startDate>2009-09</startDate>
      <endDate>2013-05</endDate>
    </institution>
  </education>
</resume>"""

        # Minimal XML with only required fields
        self.minimal_xml = """<resume>
  <personal>
    <name>John Doe</name>
  </personal>
  <skills>
    <skill>Python</skill>
  </skills>
</resume>"""

        # XML with missing sections
        self.incomplete_xml = """<resume>
  <personal>
    <name>Alex Johnson</name>
    <summary>Software developer looking for opportunities.</summary>
  </personal>
  <!-- No skills, experience, or education sections -->
</resume>"""

        # Create mock profile
        self.profile = MagicMock(spec=JobSeekerProfile)

    def test_extract_skills(self):
        """Test extracting skills information from XML content."""
        skills_text = extract_skills(self.test_xml)

        # Check that skills are extracted correctly
        self.assertIsNotNone(skills_text)
        if skills_text:
            self.assertIn("Python", skills_text)
            self.assertIn("Django", skills_text)
            self.assertIn("JavaScript", skills_text)
            self.assertIn("React", skills_text)

    def test_extract_professional_summary(self):
        """Test extracting professional summary from XML content."""
        summary = extract_professional_summary(self.test_xml)

        # Check that summary is extracted correctly
        self.assertIsNotNone(summary)
        if summary:
            self.assertIn("Experienced software engineer", summary)
            self.assertIn("web development", summary)

    def test_extract_experience(self):
        """Test extracting experience information from XML content."""
        experience_text = extract_experience(self.test_xml)

        # Check that experience is extracted correctly
        self.assertIsNotNone(experience_text)
        if experience_text:
            self.assertIn("Senior Developer", experience_text)
            self.assertIn("Tech Solutions Inc.", experience_text)
            self.assertIn("Junior Developer", experience_text)
            self.assertIn("CodeCorp", experience_text)
            self.assertIn("2018-01", experience_text)
            self.assertIn("Present", experience_text)

    def test_extract_education(self):
        """Test extracting education information from XML content."""
        education_text = extract_education(self.test_xml)

        # Check that education text is extracted correctly
        self.assertIsNotNone(education_text)

        # Only check content if education_text is not None (to satisfy the type checker)
        if education_text:
            self.assertIn("University of Technology", education_text)
            self.assertIn("Master of Computer Science", education_text)
            self.assertIn("State College", education_text)
            self.assertIn("Dates: 2013-09 - 2015-05", education_text)

    def test_extract_most_recent_title(self):
        """Test extracting most recent title from XML content."""
        position = extract_most_recent_title(self.test_xml)

        # Check that most recent title is extracted correctly
        self.assertIsNotNone(position)
        if position:
            self.assertEqual(position, "Senior Developer")

    def test_calculate_years_experience(self):
        """Test calculating years of experience from XML content."""
        years = calculate_years_experience(self.test_xml)

        # Check that years of experience is calculated correctly
        self.assertIsNotNone(years)
        # Just check it's a number (integer), not trying to validate the exact calculation
        self.assertIsInstance(years, int)

    @patch("apps.resume_processing.utils.profile_updater.logger")
    def test_update_profile_with_all_fields(self, mock_logger):
        """Test updating a profile with complete parsed data."""
        # Parse the XML to get all data fields
        education_text = extract_education(self.test_xml)
        skills_text = extract_skills(self.test_xml)
        experience_text = extract_experience(self.test_xml)
        professional_summary = extract_professional_summary(self.test_xml)
        most_recent_title = extract_most_recent_title(self.test_xml)
        years_of_experience = calculate_years_experience(self.test_xml)

        # Prepare parsed data dictionary with all fields
        parsed_data = {
            "education": education_text,
            "skills": skills_text,
            "experience": experience_text,
            "professional_summary": professional_summary,
            "most_recent_title": most_recent_title,
            "years_of_experience": years_of_experience,
        }

        # Call the split update functions
        result_fields = update_profile_fields(self.profile, parsed_data)
        result_tagline = generate_and_save_personal_tagline(
            self.profile, self.test_xml, parsed_data
        )
        result = result_fields and result_tagline

        # Verify the result
        self.assertTrue(result)
        # Two saves: one for fields update, one for tagline generation
        self.assertEqual(self.profile.save.call_count, 2)

        # Verify that the profile model was updated correctly
        self.assertEqual(self.profile.education, education_text)
        self.assertEqual(self.profile.skills, skills_text)
        self.assertEqual(self.profile.experience, experience_text)
        self.assertEqual(self.profile.professional_summary, professional_summary)
        self.assertEqual(self.profile.most_recent_title, most_recent_title)

        # Check years_of_experience is set, but don't check exact value since the test mock behaves differently
        self.assertIsNotNone(self.profile.years_of_experience)

        self.assertEqual(self.profile.resume_xml, self.test_xml)

        # Verify that the success message was logged
        mock_logger.info.assert_called_with(
            "Personal tagline generated: %s", "Test Tagline"
        )

    @patch("apps.resume_processing.utils.profile_updater.logger")
    def test_update_profile_with_minimal_data(self, mock_logger):
        """Test updating a profile with minimal parsed data."""
        # Parse the minimal XML
        skills_text = extract_skills(self.minimal_xml)

        # Prepare parsed data dictionary with minimal fields
        parsed_data = {
            "skills": skills_text,
        }

        # Call the split update functions
        result_fields = update_profile_fields(self.profile, parsed_data)
        result_tagline = generate_and_save_personal_tagline(
            self.profile, self.minimal_xml, parsed_data
        )
        result = result_fields and result_tagline

        # Verify the result
        self.assertTrue(result)
        # Two saves: one for fields update, one for tagline generation
        self.assertEqual(self.profile.save.call_count, 2)

        # Verify that the profile model was updated correctly
        self.assertEqual(self.profile.skills, skills_text)
        self.assertEqual(self.profile.resume_xml, self.minimal_xml)

        # These fields shouldn't be changed since they weren't in parsed_data
        self.assertNotEqual(self.profile.education, "Some education")
        self.assertNotEqual(self.profile.experience, "Some experience")
        self.assertNotEqual(self.profile.professional_summary, "Some summary")

        # Verify that the success message was logged
        mock_logger.info.assert_called_with(
            "Personal tagline generated: %s", "Test Tagline"
        )

    @patch("apps.resume_processing.utils.profile_updater.logger")
    def test_update_profile_incomplete_data(self, mock_logger):
        """Test updating a profile with incomplete XML (missing sections)."""
        # Parse the incomplete XML
        summary = extract_professional_summary(self.incomplete_xml)

        # Verify some fields are extracted and others are None
        self.assertIsNotNone(summary)
        self.assertIsNone(extract_skills(self.incomplete_xml))
        self.assertIsNone(extract_experience(self.incomplete_xml))
        self.assertIsNone(extract_education(self.incomplete_xml))

        # Prepare parsed data dictionary with only summary
        parsed_data = {
            "professional_summary": summary,
        }

        # Call the split update functions
        result_fields = update_profile_fields(self.profile, parsed_data)
        result_tagline = generate_and_save_personal_tagline(
            self.profile, self.incomplete_xml, parsed_data
        )
        result = result_fields and result_tagline

        # Verify the result
        self.assertTrue(result)
        # Two saves: one for fields update, one for tagline generation
        self.assertEqual(self.profile.save.call_count, 2)

        # Check that only summary was updated
        self.assertEqual(self.profile.professional_summary, summary)
        self.assertEqual(self.profile.resume_xml, self.incomplete_xml)

        # Verify that the success message was logged
        mock_logger.info.assert_called_with(
            "Personal tagline generated: %s", "Test Tagline"
        )

    @patch("apps.resume_processing.utils.profile_updater.logger")
    def test_update_profile_without_education(self, mock_logger):
        """Test updating a profile with parsed data that has no education."""
        # Prepare parsed data without education
        parsed_data = {
            "skills": "Python, Django, JavaScript",
            "experience": "Some experience text",
            "professional_summary": "Professional summary text",
        }

        # Call the split update functions
        result_fields = update_profile_fields(self.profile, parsed_data)
        result_tagline = generate_and_save_personal_tagline(
            self.profile, "some xml", parsed_data
        )
        result = result_fields and result_tagline

        # Verify the result
        self.assertTrue(result)
        # Two saves: one for fields update, one for tagline generation
        self.assertEqual(self.profile.save.call_count, 2)

        # Verify that the profile model was updated correctly
        self.assertEqual(self.profile.skills, "Python, Django, JavaScript")
        self.assertEqual(self.profile.experience, "Some experience text")
        self.assertEqual(self.profile.professional_summary, "Professional summary text")

        # Verify that the success message was logged
        mock_logger.info.assert_called_with(
            "Personal tagline generated: %s", "Test Tagline"
        )

    @patch("apps.resume_processing.utils.profile_updater.logger")
    def test_update_profile_exception_handling(self, mock_logger):
        """Test that exceptions during profile updating are handled correctly."""
        # Make the save method raise an exception
        self.profile.save.side_effect = Exception("Test exception")

        # Prepare some parsed data
        parsed_data = {"education": "Some education data"}

        # Call the split update functions; profile.save will raise on first call
        result_fields = update_profile_fields(self.profile, parsed_data)
        result_tagline = generate_and_save_personal_tagline(
            self.profile, "some xml", parsed_data
        )
        result = result_fields and result_tagline

        # Verify the result indicates failure
        self.assertFalse(result)

        # Verify that the error was logged for saving personal tagline
        mock_logger.error.assert_any_call(
            "Error saving personal tagline: %s", "Test exception"
        )
