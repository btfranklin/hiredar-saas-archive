"""
Tests for the signal handlers in the matching app.

This module tests the handling of signals for job openings and talent sheets,
particularly focusing on embedding management during status transitions.
"""

from unittest.mock import call, patch

from django.apps import apps
from django.test import TestCase

from apps.matching.signals import (
    handle_job_opening_delete,
    handle_job_opening_save,
    handle_talent_sheet_delete,
    handle_talent_sheet_save,
)


class JobOpeningSignalTests(TestCase):
    """Test signal handlers for JobOpening status transitions."""

    def setUp(self):
        """Set up test data."""
        # Get the models dynamically to avoid circular imports
        self.JobOpening = apps.get_model("recruiters", "JobOpening")
        self.User = apps.get_model("authentication", "User")
        self.RecruiterProfile = apps.get_model("recruiters", "RecruiterProfile")

        # Create a test user and recruiter
        self.test_user = self.User.objects.create_user(
            username="test_recruiter",
            email="test@example.com",
            password="password123",
            user_type="recruiter",
            name="Test Recruiter",
        )

        # The RecruiterProfile should have been created automatically via signal
        self.test_recruiter = self.RecruiterProfile.objects.get(user=self.test_user)

    @patch("apps.matching.signals.async_task")
    def test_job_opening_save_handler(self, mock_async_task):
        """Test the job opening save handler processes status transitions correctly."""
        # Test with an active job
        job_active = self.JobOpening(
            id=1,  # Use a fixed ID for testing
            recruiter=self.test_recruiter,
            title="Test Job",
            description="This is a test job",
            status="active",
        )

        # Call the signal handler directly
        handle_job_opening_save(
            sender=self.JobOpening, instance=job_active, created=True
        )

        # Verify that create_job_opening_embeddings was called for active job
        mock_async_task.assert_called_with(
            "apps.matching.tasks.create_job_opening_embeddings", job_active.id
        )

        # Reset mock
        mock_async_task.reset_mock()

        # Test with a draft job
        job_draft = self.JobOpening(
            id=2,  # Use a fixed ID for testing
            recruiter=self.test_recruiter,
            title="Test Job",
            description="This is a test job",
            status="draft",
        )

        # Call the signal handler directly
        handle_job_opening_save(
            sender=self.JobOpening, instance=job_draft, created=True
        )

        # Verify both task calls for non-active job
        expected_calls = [
            call("apps.matching.tasks.remove_job_opening_embeddings", job_draft.id),
            call("apps.matching.tasks.remove_job_opening_matches", job_draft.id),
        ]
        mock_async_task.assert_has_calls(expected_calls, any_order=True)

        # Reset mock
        mock_async_task.reset_mock()

        # Test with a closed job
        job_closed = self.JobOpening(
            id=3,  # Use a fixed ID for testing
            recruiter=self.test_recruiter,
            title="Test Job",
            description="This is a test job",
            status="closed",
        )

        # Call the signal handler directly
        handle_job_opening_save(
            sender=self.JobOpening, instance=job_closed, created=True
        )

        # Verify both task calls for non-active job
        expected_calls = [
            call("apps.matching.tasks.remove_job_opening_embeddings", job_closed.id),
            call("apps.matching.tasks.remove_job_opening_matches", job_closed.id),
        ]
        mock_async_task.assert_has_calls(expected_calls, any_order=True)

    @patch("apps.matching.signals.async_task")
    def test_job_opening_delete_handler(self, mock_async_task):
        """Test the job opening delete handler."""
        # Create a job instance
        job = self.JobOpening(
            id=4,  # Use a fixed ID for testing
            recruiter=self.test_recruiter,
            title="Test Job",
            description="This is a test job",
            status="active",
        )

        # Call the delete handler directly
        handle_job_opening_delete(sender=self.JobOpening, instance=job)

        # Verify both task calls for delete handler
        expected_calls = [
            call("apps.matching.tasks.remove_job_opening_embeddings", job.id),
            call("apps.matching.tasks.remove_job_opening_matches", job.id),
        ]
        mock_async_task.assert_has_calls(expected_calls, any_order=True)


class TalentSheetSignalTests(TestCase):
    """Test signal handlers for TalentSheet status transitions."""

    def setUp(self):
        """Set up test data."""
        # Get the models dynamically to avoid circular imports
        self.TalentSheet = apps.get_model("job_seekers", "TalentSheet")
        self.User = apps.get_model("authentication", "User")
        self.JobSeekerProfile = apps.get_model("job_seekers", "JobSeekerProfile")

        # Create a test user with job_seeker type
        self.test_user = self.User.objects.create_user(
            username="test_jobseeker",
            email="jobseeker@example.com",
            password="password123",
            user_type="job_seeker",
            name="Test Job Seeker",
        )

        # Get the JobSeekerProfile that was automatically created via signal
        self.test_job_seeker = self.JobSeekerProfile.objects.get(
            user_owner=self.test_user
        )

    @patch("apps.matching.signals.async_task")
    def test_talent_sheet_save_handler(self, mock_async_task):
        """Test the talent sheet save handler handles publish status correctly."""
        # Test with a published talent sheet
        talent_published = self.TalentSheet(
            id=1,  # Use a fixed ID for testing
            job_seeker=self.test_job_seeker,
            promotional_blurb="Test talent sheet",
            is_published=True,
        )

        # Call the signal handler directly
        handle_talent_sheet_save(
            sender=self.TalentSheet, instance=talent_published, created=True
        )

        # Verify that create_talent_sheet_embeddings was called for published talent sheet
        mock_async_task.assert_called_with(
            "apps.matching.tasks.create_talent_sheet_embeddings", talent_published.id
        )

        # Reset mock
        mock_async_task.reset_mock()

        # Test with an unpublished talent sheet
        talent_unpublished = self.TalentSheet(
            id=2,  # Use a fixed ID for testing
            job_seeker=self.test_job_seeker,
            promotional_blurb="Test talent sheet",
            is_published=False,
        )

        # Call the signal handler directly
        handle_talent_sheet_save(
            sender=self.TalentSheet, instance=talent_unpublished, created=True
        )

        # Verify both task calls for unpublished talent sheet
        expected_calls = [
            call(
                "apps.matching.tasks.remove_talent_sheet_embeddings",
                talent_unpublished.id,
            ),
            call(
                "apps.matching.tasks.remove_talent_sheet_matches", talent_unpublished.id
            ),
        ]
        mock_async_task.assert_has_calls(expected_calls, any_order=True)

    @patch("apps.matching.signals.async_task")
    def test_talent_sheet_delete_handler(self, mock_async_task):
        """Test the talent sheet delete handler."""
        # Create a talent sheet instance
        talent = self.TalentSheet(
            id=3,  # Use a fixed ID for testing
            job_seeker=self.test_job_seeker,
            promotional_blurb="Test talent sheet",
            is_published=True,
        )

        # Call the delete handler directly
        handle_talent_sheet_delete(sender=self.TalentSheet, instance=talent)

        # Verify both task calls for delete handler
        expected_calls = [
            call("apps.matching.tasks.remove_talent_sheet_embeddings", talent.id),
            call("apps.matching.tasks.remove_talent_sheet_matches", talent.id),
        ]
        mock_async_task.assert_has_calls(expected_calls, any_order=True)
