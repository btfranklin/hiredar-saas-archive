"""
Unit tests for matching app signal handlers.

This module tests the signal handlers that trigger task execution
for embedding and matching operations in response to model changes.
"""

from unittest.mock import Mock, call, patch

from django.apps import apps
from django.test import TestCase

from apps.matching import signals
from apps.matching.signals import (
    handle_job_opening_delete,
    handle_job_opening_save,
    handle_talent_sheet_delete,
    handle_talent_sheet_save,
)

# Monkey-patch transaction.on_commit to execute callbacks immediately in tests
signals.transaction.on_commit = lambda func: func()


class JobOpeningSignalTests(TestCase):
    """Test signal handlers for JobOpening status transitions."""

    def setUp(self):
        """Set up test data."""
        # Get the models dynamically to avoid circular imports
        self.JobOpening = apps.get_model("recruiters", "JobOpening")
        self.User = apps.get_model("authentication", "User")
        self.RecruiterProfile = apps.get_model("recruiters", "RecruiterProfile")

        # Create a test user with recruiter type
        self.test_user = self.User.objects.create_user(
            username="test_recruiter",
            email="recruiter@example.com",
            password="password123",
            user_type="recruiter",
            name="Test Recruiter",
        )

        # The RecruiterProfile should have been created automatically via signal
        self.test_recruiter = self.RecruiterProfile.objects.get(user=self.test_user)

    @patch("apps.matching.signals.chain")
    @patch("apps.matching.signals.async_task")
    def test_job_opening_save_handler(self, mock_async_task, mock_chain):
        """Test the job opening save handler processes status transitions correctly."""
        # Set up chain mock
        mock_chain_instance = Mock()
        mock_chain.return_value = mock_chain_instance

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

        # Verify that chain was called with proper tasks
        mock_chain.assert_called_once()
        args = mock_chain.call_args[0]
        self.assertEqual(len(args), 2)  # Should have 2 tasks in chain

        # Verify apply_async was called
        mock_chain_instance.apply_async.assert_called_once()

        # Reset mocks
        mock_async_task.reset_mock()
        mock_chain.reset_mock()

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

        # Verify both task calls for non-active job (uses async_task)
        expected_calls = [
            call(
                signals.remove_job_opening_embeddings,
                job_draft.id,
                task_name=f"remove_job_embeddings_{job_draft.id}",
            ),
            call(
                signals.remove_job_opening_matches,
                job_draft.id,
                task_name=f"remove_job_matches_{job_draft.id}",
            ),
        ]
        mock_async_task.assert_has_calls(expected_calls, any_order=True)

        # Reset mocks
        mock_async_task.reset_mock()
        mock_chain.reset_mock()

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

        # Verify both task calls for non-active job (uses async_task)
        expected_calls = [
            call(
                signals.remove_job_opening_embeddings,
                job_closed.id,
                task_name=f"remove_job_embeddings_{job_closed.id}",
            ),
            call(
                signals.remove_job_opening_matches,
                job_closed.id,
                task_name=f"remove_job_matches_{job_closed.id}",
            ),
        ]
        mock_async_task.assert_has_calls(expected_calls, any_order=True)

        # Reset mocks
        mock_async_task.reset_mock()
        mock_chain.reset_mock()

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
            call(
                signals.remove_job_opening_embeddings,
                job.id,
                task_name=f"cleanup_job_embeddings_{job.id}",
            ),
            call(
                signals.remove_job_opening_matches,
                job.id,
                task_name=f"cleanup_job_matches_{job.id}",
            ),
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

    @patch("apps.matching.signals.chain")
    @patch("apps.matching.signals.async_task")
    def test_talent_sheet_save_handler(self, mock_async_task, mock_chain):
        """Test the talent sheet save handler handles publish status correctly."""
        # Set up chain mock
        mock_chain_instance = Mock()
        mock_chain.return_value = mock_chain_instance

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

        # Verify that chain was called with proper tasks
        mock_chain.assert_called_once()
        args = mock_chain.call_args[0]
        self.assertEqual(len(args), 2)  # Should have 2 tasks in chain

        # Verify apply_async was called
        mock_chain_instance.apply_async.assert_called_once()

        # Reset mocks
        mock_async_task.reset_mock()
        mock_chain.reset_mock()

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
                signals.remove_talent_sheet_embeddings,
                talent_unpublished.id,
                task_name=f"remove_talent_embeddings_{talent_unpublished.id}",
            ),
            call(
                signals.remove_talent_sheet_matches,
                talent_unpublished.id,
                task_name=f"remove_talent_matches_{talent_unpublished.id}",
            ),
        ]
        mock_async_task.assert_has_calls(expected_calls, any_order=True)

        # Reset mocks
        mock_async_task.reset_mock()
        mock_chain.reset_mock()

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
            call(
                signals.remove_talent_sheet_embeddings,
                talent.id,
                task_name=f"cleanup_talent_embeddings_{talent.id}",
            ),
            call(
                signals.remove_talent_sheet_matches,
                talent.id,
                task_name=f"cleanup_talent_matches_{talent.id}",
            ),
        ]
        mock_async_task.assert_has_calls(expected_calls, any_order=True)
