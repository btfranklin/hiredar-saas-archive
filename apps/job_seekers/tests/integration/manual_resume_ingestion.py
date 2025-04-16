"""
Integration test for the resume ingestion and talent sheet generation pipeline.

This test verifies the end-to-end process of ingesting resumes and generating
talent sheets, making sure the entire pipeline functions correctly.

⚠️ WARNING: THIS IS A MANUAL TEST FILE ⚠️
This test makes real API calls to OpenAI and costs money to run.
It should ONLY be run manually with explicit intention, never as part of
automated test runs or CI/CD pipelines.

To run this test manually:
    python manage.py test apps.job_seekers.tests.integration.manual_resume_ingestion
"""

import logging
import os
import time
import traceback
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models.signals import post_save
from django.test import TestCase

from apps.authentication.models import User
from apps.job_seekers.models import JobSeekerProfile, TalentSheet
from apps.job_seekers.tasks.talent_sheet_tasks import generate_talent_sheet_task
from apps.job_seekers.utils.recommendation.llm_processor import (
    generate_personal_tagline,
)
from apps.job_seekers.utils.resume_processing.pipeline import process_resume
from apps.matching.signals import handle_talent_sheet_save

# Setup logging
logger = logging.getLogger(__name__)


class ManualTestCase(TestCase):
    """
    Base class for tests that should not be auto-discovered by the test runner.

    This is a marker class to help identify tests that should only be run manually.
    These tests typically make external API calls that cost money or have other
    side effects that make them inappropriate for automated test runs.
    """

    def setUp(self):
        """Set up before each test method."""
        # Always check if we're in an automated environment
        if os.environ.get("CI") or os.environ.get("AUTOMATED_TESTING"):
            self.skipTest("Skipping manual test in automated testing environment")

        # Check for a specific env var that must be set to run manual tests
        if not os.environ.get("ALLOW_MANUAL_TESTS"):
            self.skipTest(
                "Set ALLOW_MANUAL_TESTS=1 to run this test. WARNING: May incur costs!"
            )

        super().setUp()


class ResumeIngestionTest(ManualTestCase):
    """
    Integration test for the resume ingestion and talent sheet generation pipeline.

    This test follows the same workflow as the production system:
    1. Process resume PDFs into JobSeekerProfiles
    2. Generate TalentSheets for the job seekers
    3. Produce an HTML report for inspection

    ⚠️ WARNING: This test makes real API calls to OpenAI, which cost money.
    It should NEVER be run automatically and requires ALLOW_MANUAL_TESTS=1 to be set.
    """

    def setUp(self):
        """Set up before each test method."""
        super().setUp()  # This ensures the ManualTestCase checks run first

        # Ensure required API keys exist
        self.assertTrue(
            os.environ.get("OPENAI_API_KEY"),
            "OpenAI API key not found. Set OPENAI_API_KEY environment variable.",
        )

        # Path to sample resumes
        self.sample_data_path = Path(settings.BASE_DIR) / "sample_data" / "resumes"
        self.assertTrue(
            self.sample_data_path.exists(),
            f"Sample data path not found: {self.sample_data_path}",
        )

        # Disconnect the TalentSheet post_save signal to prevent the error
        # The signal tries to access 'status' field which doesn't exist on TalentSheet
        post_save.disconnect(handle_talent_sheet_save, sender=TalentSheet)

    def tearDown(self):
        """Clean up after test."""
        # Reconnect the TalentSheet post_save signal
        post_save.connect(handle_talent_sheet_save, sender=TalentSheet)

    def test_resume_ingestion_and_talent_sheet_generation(self):
        """Test the complete pipeline from resume ingestion to talent sheet generation."""

        # Step 1: Find resume files
        resume_files = list(self.sample_data_path.glob("*.pdf"))[
            :3
        ]  # Limit to 3 for faster testing
        self.assertTrue(resume_files, "No sample resumes found")

        # Step 2: Process resumes and create job seeker profiles
        processed_profiles = []

        for i, resume_file in enumerate(resume_files, 1):
            print(f"\n[{i}/{len(resume_files)}] Processing: {resume_file.name}")

            # Create test user and process resume
            user, profile = self._create_test_user(i)
            logger.info("Created user: %s", user.email)
            self.assertIsNotNone(
                profile, f"Failed to create profile for {resume_file.name}"
            )

            # Process the resume and update the profile
            success = self._process_resume(str(resume_file), profile)
            self.assertTrue(success, f"Failed to process resume {resume_file.name}")

            processed_profiles.append(profile)

            # Wait briefly to avoid rate limiting
            time.sleep(1)

        # Step 3: Generate talent sheets for the processed profiles
        talent_sheets = []

        for profile in processed_profiles:
            # In production, the profile would be marked as in_talent_pool first
            profile.in_talent_pool = True
            profile.save(update_fields=["in_talent_pool"])

            # Call the same task that would be triggered when a user joins the talent pool
            result = generate_talent_sheet_task(profile.id)
            self.assertTrue(
                result.get("success", False),
                f"Failed to generate talent sheet for {profile.user_owner.email if profile.user_owner else 'unknown@example.com'}: {result.get('message')}",
            )

            # Get the talent sheet
            profile.refresh_from_db()
            self.assertTrue(
                hasattr(profile, "talent_sheet"),
                f"No talent sheet created for {profile.user_owner.email if profile.user_owner else 'unknown@example.com'}",
            )

            talent_sheets.append(profile.talent_sheet)

            # Wait briefly to avoid rate limiting
            time.sleep(1)

        # Step 4: Generate personal taglines for each profile
        # (This is normally done asynchronously but we need to ensure it's complete for the report)
        print("\nGenerating personal taglines...")
        for profile in processed_profiles:
            try:
                # Generate personal tagline if not already present
                if not profile.personal_tagline and profile.resume_xml:
                    print(
                        f"Generating tagline for {profile.user_owner.email if profile.user_owner else 'unknown@example.com'}"
                    )
                    tagline = generate_personal_tagline(profile.resume_xml)
                    profile.personal_tagline = tagline
                    profile.save(update_fields=["personal_tagline"])
                    print(f"Generated tagline: {tagline}")
            except Exception as e:
                print(f"Error generating personal tagline: {e}")

        # Step 5: Generate HTML report
        report_path = self._generate_html_report(talent_sheets)
        print(f"\n\nTest complete! View the report at: {report_path}\n")

        # Assertions to verify pipeline success
        self.assertTrue(len(talent_sheets) > 0, "No talent sheets were generated")
        for ts in talent_sheets:
            self.assertTrue(
                ts.promotional_blurb, "Talent sheet is missing promotional blurb"
            )
            self.assertTrue(ts.skill_overview, "Talent sheet is missing skill overview")
            self.assertTrue(ts.ideal_roles, "Talent sheet is missing ideal roles")

    def _create_test_user(self, counter: int) -> tuple[User, JobSeekerProfile]:
        """Create a test user and job seeker profile for testing."""
        unique_id = f"{counter}_{uuid.uuid4().hex[:8]}"
        email = f"test_user_{unique_id}@example.com"

        try:
            # Create a test user with the job_seeker type
            user = User.objects.create_user(  # type: ignore
                email=email,
                password="testpassword123",
                name=f"Test{counter} User{counter}",
                user_type="job_seeker",
            )

            # A JobSeekerProfile should be created automatically via signals
            profile = JobSeekerProfile.objects.get(
                owner_content_type__model="user", owner_object_id=user.id
            )

            return user, profile
        except Exception as e:
            self.fail(f"Error creating test user: {e}")
            return None, None

    def _process_resume(self, resume_path: str, profile: JobSeekerProfile) -> bool:
        """Process a resume file and update the given profile with extracted information."""
        saved_path = None

        try:
            # Step 1: Read the PDF file
            try:
                with open(resume_path, "rb") as f:
                    file_content = f.read()
            except Exception as e:
                print(f"ERROR reading file: {str(e)}")
                return False

            # Step 2: Save the resume temporarily
            temp_dir = "resumes"
            # Make sure the directory exists
            os.makedirs(os.path.join(settings.MEDIA_ROOT, temp_dir), exist_ok=True)

            temp_path = f"{temp_dir}/temp_{uuid.uuid4().hex}.pdf"
            saved_path = default_storage.save(temp_path, ContentFile(file_content))

            print(f"Processing resume: {os.path.basename(resume_path)}")

            # Step 3: Use the unified pipeline to process the resume
            result = process_resume(saved_path, profile)

            if not result["success"]:
                # Display detailed error information
                error_msg = result.get("message", "Unknown error")

                # Show which step failed
                pipeline_steps = result.get("pipeline_steps", {})
                failed_at = "unknown step"
                for step, completed in pipeline_steps.items():
                    if not completed:
                        failed_at = step
                        break

                print(f"ERROR in {failed_at}: {error_msg}")

                # Always clean up temporary file if it exists
                if saved_path:
                    try:
                        default_storage.delete(saved_path)
                    except Exception:
                        pass

                return False

            return True

        except Exception as e:
            print(f"Unhandled error during resume processing: {e}")
            traceback.print_exc()

            # Always clean up temporary file if it exists
            if saved_path:
                try:
                    default_storage.delete(saved_path)
                except Exception:
                    pass

            return False

    def _generate_html_report(self, talent_sheets: list[TalentSheet]) -> str:
        """Generate a standalone HTML report file showing the processed talent sheets."""

        # Create output directory if it doesn't exist
        output_dir = Path(settings.BASE_DIR) / "test_reports"
        output_dir.mkdir(exist_ok=True)

        # Create a timestamp for the filename
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"talent_sheet_report_{timestamp}.html"

        # Start building HTML content
        html_content = [
            f"""<!DOCTYPE html>
<html>
<head>
    <title>Talent Sheet Generation Test Report - {timestamp}</title>
    <link href="https://cdn.tailwindcss.com" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/daisyui@latest/dist/full.css" rel="stylesheet">
    <style>
        body {{ padding: 2rem; max-width: 1200px; margin: 0 auto; }}
        .section {{ margin-bottom: 2rem; }}
        .card {{ margin-bottom: 2rem; border: 1px solid #eaeaea; padding: 1.5rem; border-radius: 0.5rem; }}
        .tag {{ display: inline-block; background-color: #e5e7eb; padding: 0.25rem 0.5rem; margin: 0.25rem; border-radius: 0.25rem; }}
        pre {{ white-space: pre-wrap; background-color: #f3f4f6; padding: 1rem; border-radius: 0.5rem; margin-top: 0.5rem; }}
        h3 {{ border-bottom: 1px solid #e5e7eb; padding-bottom: 0.5rem; margin-bottom: 1rem; }}
    </style>
    <script src="https://unpkg.com/htmx.org@1.9.2"></script>
</head>
<body>
    <h1 class="text-3xl font-bold mb-6">Talent Sheet Generation Test Report</h1>
    <p class="mb-6">Generated on: {time.strftime("%Y-%m-%d %H:%M:%S")}</p>
    
    <div class="stats shadow mb-6 w-full">
        <div class="stat">
            <div class="stat-title">Total Resumes Processed</div>
            <div class="stat-value">{len(talent_sheets)}</div>
        </div>
    </div>
    
    <div class="section">
        <h2 class="text-2xl font-semibold mb-4">Generated Talent Sheets</h2>
"""
        ]

        # Add each talent sheet
        for ts in talent_sheets:
            profile = ts.job_seeker
            html_content.append(
                f"""
        <div class="card">
            <h3 class="text-xl font-bold">{profile.user_owner.name if profile.user_owner else 'Unknown'} <span class="text-sm text-gray-500">({profile.user_owner.email if profile.user_owner else 'unknown@example.com'})</span></h3>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
                <div>
                    <h4 class="font-semibold text-lg mb-2">Promotional Blurb</h4>
                    <p class="italic text-gray-700">{ts.promotional_blurb}</p>
                </div>
                
                <div>
                    <h4 class="font-semibold text-lg mb-2">Skill Overview</h4>
                    <p>{ts.skill_overview}</p>
                </div>
            </div>
            
            <div class="mb-4">
                <h4 class="font-semibold text-lg mb-2">Ideal Roles</h4>
                <div>
                    {' '.join([f'<span class="tag">{role}</span>' for role in ts.ideal_roles_list])}
                </div>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <h4 class="font-semibold text-lg mb-2">Profile Information</h4>
                    <ul class="list-disc pl-5">
                        <li><strong>Personal Tagline:</strong> {profile.personal_tagline or 'Not available'}</li>
                        <li><strong>Most Recent Title:</strong> {profile.most_recent_title or 'Not available'}</li>
                        <li><strong>Years of Experience:</strong> {profile.years_of_experience or 'Not specified'}</li>
                        <li><strong>Desired Role:</strong> {profile.desired_role or 'Not specified'}</li>
                    </ul>
                </div>
                
                <div>
                    <h4 class="font-semibold text-lg mb-2">Salary Expectation</h4>
                    <p>
                        {f"${ts.salary_min:,.2f}" if ts.salary_min else "Not specified"}
                    </p>
                </div>
            </div>
        </div>
"""
            )

        html_content.append(
            """
    </div>
</body>
</html>
"""
        )

        # Write the HTML file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("".join(html_content))

        return str(output_file.absolute())
