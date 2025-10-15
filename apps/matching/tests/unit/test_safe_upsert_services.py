"""
Tests for race condition fixes in matching operations.
"""

from decimal import Decimal
from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase

from apps.authentication.models import User
from apps.candidates.models import CandidatePool
from apps.core.services.task_idempotency import IdempotentTaskManager
from apps.job_seekers.models import JobSeekerProfile, TalentSheet
from apps.job_seekers.services.talent_sheet_service import TalentSheetService
from apps.matching.models import CandidateMatch
from apps.matching.services.candidate_match_service import CandidateMatchService
from apps.recruiters.models import JobOpening, RecruiterProfile


class RaceConditionTests(TestCase):
    """Behavioral tests for the safe upsert helpers."""

    @classmethod
    def setUpTestData(cls):
        """Create shared fixtures for race-condition tests."""
        cls.recruiter_user = User.objects.create_user(
            email="recruiter@test.com",
            password="testpass",
            user_type="recruiter",
            name="Test Recruiter",
        )
        cls.recruiter_profile = RecruiterProfile.objects.get(user=cls.recruiter_user)

        cls.job_opening = JobOpening.objects.create(
            recruiter=cls.recruiter_profile,
            title="Test Job",
            description="Test job description",
            status="active",
        )

        cls.candidate_pool = CandidatePool.objects.create(
            recruiter=cls.recruiter_user, name="Race Condition Pool"
        )
        cls.job_seeker_profile = JobSeekerProfile.objects.create(
            candidate_pool=cls.candidate_pool,
            candidate_name="Race Condition Candidate",
        )
        cls.talent_sheet = TalentSheet.objects.create(
            job_seeker=cls.job_seeker_profile,
            promotional_blurb="Initial blurb",
            experience_overview="Initial experience",
            is_published=True,
        )

        cls.secondary_job_seeker = JobSeekerProfile.objects.create(
            candidate_pool=cls.candidate_pool,
            candidate_name="Second Candidate",
        )

    def test_safe_upsert_candidate_match_creates_once_and_updates(self):
        """Repeated upserts should reuse the same CandidateMatch."""
        match, created = CandidateMatchService.safe_upsert_candidate_match(
            job_opening_id=self.job_opening.id,
            talent_sheet_id=self.talent_sheet.id,
            score_updates={
                "holistic": 0.5,
                "skills": 0.6,
                "experience": 0.7,
            },
            is_analyzed=False,
        )

        self.assertTrue(created)
        self.assertEqual(CandidateMatch.objects.count(), 1)

        updated_match, updated_created = CandidateMatchService.safe_upsert_candidate_match(
            job_opening_id=self.job_opening.id,
            talent_sheet_id=self.talent_sheet.id,
            score_updates={
                "holistic": 0.8,
                "skills": 0.3,
                "experience": 0.4,
                "wildcard": 0.9,
            },
            is_analyzed=True,
        )

        self.assertFalse(updated_created)
        self.assertEqual(match.pk, updated_match.pk)
        updated_match.refresh_from_db()
        self.assertAlmostEqual(float(updated_match.holistic_score), 0.8)
        self.assertAlmostEqual(float(updated_match.skills_score), 0.3)
        self.assertAlmostEqual(float(updated_match.wildcard_score), 0.9)
        self.assertTrue(updated_match.is_analyzed)

    def test_safe_upsert_candidate_match_handles_integrity_error(self):
        """IntegrityError during creation should retry and update the row."""
        CandidateMatch.objects.all().delete()
        real_create = CandidateMatch.objects.create
        created_flag = {"done": False}

        def fake_create(*args, **kwargs):
            if not created_flag["done"]:
                created_flag["done"] = True
                real_create(
                    job_opening=kwargs["job_opening"],
                    talent_sheet=kwargs["talent_sheet"],
                    holistic_score=Decimal("0.1"),
                    skills_score=Decimal("0.1"),
                    experience_score=Decimal("0.1"),
                    wildcard_score=Decimal("0.1"),
                    qualifications_score=Decimal("0.1"),
                    is_analyzed=True,
                )
            raise IntegrityError("simulated concurrent insert")

        with patch(
            "apps.matching.models.candidate_match.CandidateMatch.objects.create",
            side_effect=fake_create,
        ):
            match, created = CandidateMatchService.safe_upsert_candidate_match(
                job_opening_id=self.job_opening.id,
                talent_sheet_id=self.talent_sheet.id,
                score_updates={
                    "holistic": 0.75,
                    "skills": 0.65,
                    "experience": 0.55,
                    "wildcard": 0.45,
                    "qualifications": 0.35,
                },
                is_analyzed=False,
            )

        self.assertFalse(created)
        self.assertEqual(CandidateMatch.objects.count(), 1)
        match.refresh_from_db()
        self.assertAlmostEqual(float(match.holistic_score), 0.75)
        self.assertFalse(match.is_analyzed)

    def test_safe_upsert_talent_sheet_creates_once_and_updates(self):
        """TalentSheet upserts should reuse the same record."""
        sheet, created = TalentSheetService.safe_upsert_talent_sheet(
            job_seeker_id=self.secondary_job_seeker.id,
            talent_sheet_data={
                "promotional_blurb": "Initial blurb",
                "experience_overview": "Initial experience",
                "is_published": True,
            },
        )
        self.assertTrue(created)

        updated_sheet, updated_created = TalentSheetService.safe_upsert_talent_sheet(
            job_seeker_id=self.secondary_job_seeker.id,
            talent_sheet_data={
                "promotional_blurb": "Updated blurb",
                "experience_overview": "Updated experience",
                "ideal_roles": "Backend Engineer",
                "is_published": False,
            },
        )

        self.assertFalse(updated_created)
        self.assertEqual(sheet.pk, updated_sheet.pk)
        updated_sheet.refresh_from_db()
        self.assertEqual(updated_sheet.promotional_blurb, "Updated blurb")
        self.assertEqual(updated_sheet.ideal_roles, "Backend Engineer")
        self.assertFalse(updated_sheet.is_published)

    def test_safe_upsert_talent_sheet_handles_integrity_error(self):
        """Simulate concurrent create for TalentSheet and ensure update occurs."""
        TalentSheet.objects.filter(job_seeker=self.secondary_job_seeker).delete()
        real_create = TalentSheet.objects.create
        created_flag = {"done": False}

        def fake_create(*args, **kwargs):
            if not created_flag["done"]:
                created_flag["done"] = True
                real_create(
                    job_seeker=kwargs["job_seeker"],
                    promotional_blurb="Stale blurb",
                    experience_overview="Stale experience",
                    is_published=False,
                )
            raise IntegrityError("simulated concurrent talent sheet insert")

        with patch(
            "apps.job_seekers.models.talent_sheet.TalentSheet.objects.create",
            side_effect=fake_create,
        ):
            sheet, created = TalentSheetService.safe_upsert_talent_sheet(
                job_seeker_id=self.secondary_job_seeker.id,
                talent_sheet_data={
                    "promotional_blurb": "Fresh blurb",
                    "experience_overview": "Fresh experience",
                    "is_published": True,
                },
            )

        self.assertFalse(created)
        self.assertEqual(
            TalentSheet.objects.filter(job_seeker=self.secondary_job_seeker).count(), 1
        )
        sheet.refresh_from_db()
        self.assertEqual(sheet.promotional_blurb, "Fresh blurb")
        self.assertTrue(sheet.is_published)


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

    @patch("apps.core.services.task_idempotency.cache")
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

    @patch("apps.core.services.task_idempotency.cache")
    def test_task_already_running_prevention(self, mock_cache):
        """Test that already running tasks are prevented."""
        mock_cache.add.return_value = False  # Simulate task already running

        task_id = "test_task_123"

        # Should not be able to mark task as running if already running
        result = IdempotentTaskManager.mark_task_running(task_id)
        self.assertFalse(result)

    @patch("apps.core.services.task_idempotency.AsyncResult")
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

    @patch("apps.core.services.task_idempotency.cache")
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

    @patch("apps.core.services.task_idempotency.cache")
    @patch("apps.core.services.task_idempotency.AsyncResult")
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
