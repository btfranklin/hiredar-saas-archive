"""
Tests for race condition fixes in matching operations.
"""

import threading
from unittest.mock import patch

from django.db import close_old_connections, transaction
from django.test import TestCase, TransactionTestCase

from apps.authentication.models import User
from apps.core.utils.task_utils import IdempotentTaskManager
from apps.job_seekers.models import JobSeekerProfile, TalentSheet
from apps.job_seekers.services.talent_sheet_service import TalentSheetService
from apps.matching.models import CandidateMatch
from apps.matching.services.candidate_match_service import CandidateMatchService
from apps.recruiters.models import JobOpening, RecruiterProfile


class RaceConditionTests(TransactionTestCase):
    """Test race condition handling in matching operations."""

    def setUp(self):
        """Set up test data."""
        # Create recruiter
        self.recruiter_user = User.objects.create_user(
            email="recruiter@test.com",
            password="testpass",
            user_type="recruiter",
            name="Test Recruiter",
        )
        self.recruiter_profile = RecruiterProfile.objects.get(user=self.recruiter_user)

        # Create job opening
        self.job_opening = JobOpening.objects.create(
            recruiter=self.recruiter_profile,
            title="Test Job",
            description="Test job description",
            status="active",
        )

        # Create job seeker
        self.job_seeker_user = User.objects.create_user(
            email="seeker@test.com",
            password="testpass",
            user_type="job_seeker",
            name="Test Seeker",
        )
        self.job_seeker_profile = JobSeekerProfile.objects.get(
            user_owner=self.job_seeker_user
        )

        # Create talent sheet
        self.talent_sheet = TalentSheet.objects.create(
            job_seeker=self.job_seeker_profile,
            promotional_blurb="Test blurb",
            experience_overview="Test experience",
            is_published=True,
        )

    def test_concurrent_candidate_match_creation(self):
        """Test that concurrent CandidateMatch creation doesn't cause race conditions."""
        results = []
        errors = []

        def create_match():
            """Create a candidate match in a separate thread."""
            try:
                close_old_connections()
                with transaction.atomic():
                    match, created = CandidateMatchService.safe_upsert_candidate_match(
                        job_opening_id=self.job_opening.id,
                        talent_sheet_id=self.talent_sheet.id,
                        score_updates={
                            "holistic": 0.8,
                            "skills": 0.7,
                            "experience": 0.9,
                        },
                        is_analyzed=False,
                    )
                    results.append((match.id, created))
            except Exception as e:
                errors.append(str(e))

        # Start multiple threads trying to create the same match
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=create_match)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have no errors
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")

        # Should have exactly one match created
        matches = CandidateMatch.objects.filter(
            job_opening=self.job_opening,
            talent_sheet=self.talent_sheet,
        )
        self.assertEqual(matches.count(), 1)

        # All results should reference the same match
        match_ids = [result[0] for result in results]
        self.assertTrue(all(match_id == match_ids[0] for match_id in match_ids))

        # Only one thread should have created the match. Background tasks may
        # pre-create the record, in which case all threads will report
        # `created=False`. Accept either outcome as long as no duplicates exist.
        created_flags = [result[1] for result in results]
        self.assertIn(sum(created_flags), {0, 1})

    def test_concurrent_talent_sheet_creation(self):
        """Test that concurrent TalentSheet creation doesn't cause race conditions."""
        # Delete the existing talent sheet
        self.talent_sheet.delete()

        results = []
        errors = []

        def create_talent_sheet():
            """Create a talent sheet in a separate thread."""
            try:
                close_old_connections()
                with transaction.atomic():
                    sheet, created = TalentSheetService.safe_upsert_talent_sheet(
                        job_seeker_id=self.job_seeker_profile.id,
                        talent_sheet_data={
                            "promotional_blurb": "Concurrent test blurb",
                            "experience_overview": "Concurrent test experience",
                            "is_published": True,
                        },
                    )
                    results.append((sheet.id, created))
            except Exception as e:
                errors.append(str(e))

        # Start multiple threads trying to create the same talent sheet
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=create_talent_sheet)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have no errors
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")

        # Should have exactly one talent sheet
        sheets = TalentSheet.objects.filter(job_seeker=self.job_seeker_profile)
        self.assertEqual(sheets.count(), 1)

        # All results should reference the same sheet
        sheet_ids = [result[0] for result in results]
        self.assertTrue(all(sheet_id == sheet_ids[0] for sheet_id in sheet_ids))

        # Only one thread should have created the sheet
        created_flags = [result[1] for result in results]
        self.assertEqual(sum(created_flags), 1)


class IdempotentTaskTests(TestCase):
    """Test idempotent task management."""

    def test_deterministic_task_id_generation(self):
        """Test that task IDs are generated deterministically."""
        task_id_1 = IdempotentTaskManager.generate_deterministic_task_id(
            "test_task", 123, "arg2"
        )
        task_id_2 = IdempotentTaskManager.generate_deterministic_task_id(
            "test_task", 123, "arg2"
        )
        task_id_3 = IdempotentTaskManager.generate_deterministic_task_id(
            "test_task", 456, "arg2"
        )

        # Same arguments should produce same ID
        self.assertEqual(task_id_1, task_id_2)

        # Different arguments should produce different ID
        self.assertNotEqual(task_id_1, task_id_3)

        # IDs should be reasonably short and contain task name
        self.assertTrue(task_id_1.startswith("test_task_"))
        self.assertLess(len(task_id_1), 50)

    @patch("apps.core.utils.task_utils.cache")
    def test_task_running_markers(self, mock_cache):
        """Test task running marker functionality."""
        mock_cache.add.return_value = True
        mock_cache.delete.return_value = None

        task_id = "test_task_123"

        # Should be able to mark task as running
        result = IdempotentTaskManager.mark_task_running(task_id)
        self.assertTrue(result)
        mock_cache.add.assert_called_with(f"task_running:{task_id}", True, timeout=3600)

        # Should be able to unmark task
        IdempotentTaskManager.unmark_task_running(task_id)
        mock_cache.delete.assert_called_with(f"task_running:{task_id}")

    @patch("apps.core.utils.task_utils.cache")
    def test_task_already_running_prevention(self, mock_cache):
        """Test that already running tasks are prevented."""
        mock_cache.add.return_value = False  # Simulate task already running

        task_id = "test_task_123"

        # Should not be able to mark task as running if already running
        result = IdempotentTaskManager.mark_task_running(task_id)
        self.assertFalse(result)

    @patch("apps.core.utils.task_utils.AsyncResult")
    def test_task_status_checking(self, mock_async_result):
        """Test task status checking functionality."""
        mock_result = mock_async_result.return_value
        mock_result.state = "STARTED"

        # Should detect running task
        is_running = IdempotentTaskManager.is_task_running("test_task_123")
        self.assertTrue(is_running)

        # Should detect completed task
        mock_result.state = "SUCCESS"
        is_running = IdempotentTaskManager.is_task_running("test_task_123")
        self.assertFalse(is_running)

    @patch("apps.core.utils.task_utils.cache")
    def test_safe_task_execution_prevents_duplicates(self, mock_cache):
        """Test that safe task execution prevents duplicate runs."""
        mock_cache.add.return_value = False  # Simulate task already running

        mock_task = lambda: None
        mock_task.apply_async = lambda *args, **kwargs: None

        # Should return None when task is already running
        result = IdempotentTaskManager.safe_task_execution(
            mock_task, "test_task", "arg1"
        )
        self.assertIsNone(result)

    @patch("apps.core.utils.task_utils.cache")
    @patch("apps.core.utils.task_utils.AsyncResult")
    def test_safe_task_execution_starts_new_task(self, mock_async_result, mock_cache):
        """Test that safe task execution starts new tasks when none running."""
        mock_cache.add.return_value = True  # Simulate no task running

        # Mock AsyncResult to return a non-running state
        mock_result_obj = mock_async_result.return_value
        mock_result_obj.state = "SUCCESS"  # Not running

        mock_result = type("MockResult", (), {"id": "task_123"})()
        mock_task = lambda: None
        mock_task.apply_async = lambda *args, **kwargs: mock_result

        # Should start new task and return task ID
        result = IdempotentTaskManager.safe_task_execution(
            mock_task, "test_task", "arg1"
        )
        self.assertEqual(result, "task_123")
