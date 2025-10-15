"""Unit tests for candidates app models."""

from django.test import TestCase

from apps.authentication.models import User
from apps.candidates.models import (
    CandidatePool,
    CandidateProfile,
    CandidateRoleRecommendation,
)
from apps.core.models import TaskMeta


class CandidatePoolModelTests(TestCase):
    """Validate helper methods on CandidatePool."""

    def setUp(self) -> None:
        self.recruiter = User.objects.create_user(  # type: ignore[attr-defined]
            email="recruiter@example.com",
            password="password",
            user_type="recruiter",
            name="Ruth Recruiter",
        )
        self.pool = CandidatePool.objects.create(
            recruiter=self.recruiter, name="April Upload"
        )

    def test_str_includes_pool_name_and_owner_email(self) -> None:
        """__str__ should surface both the pool label and recruiter email."""
        self.assertEqual(
            str(self.pool), "Candidate Pool: April Upload (recruiter@example.com)"
        )

    def test_active_task_helpers_filter_and_aggregate_states(self) -> None:
        """Only unfinished tasks should surface through helper properties."""
        pending_task = TaskMeta.objects.create(
            queue_id="task_pending",
            name="Import resumes",
            owner=self.recruiter,
            content_object=self.pool,
            state=TaskMeta.State.PENDING,
        )
        running_task = TaskMeta.objects.create(
            queue_id="task_running",
            name="Process resume",
            owner=self.recruiter,
            content_object=self.pool,
            state=TaskMeta.State.RUNNING,
        )
        TaskMeta.objects.create(
            queue_id="task_complete",
            name="Cleanup",
            owner=self.recruiter,
            content_object=self.pool,
            state=TaskMeta.State.SUCCESS,
        )

        active = self.pool.active_tasks
        self.assertEqual([pending_task, running_task], active)
        self.assertTrue(self.pool.has_active_tasks)
        self.assertCountEqual(
            self.pool.active_task_summary,
            [
                {"name": "Import resumes", "count": 1},
                {"name": "Process resume", "count": 1},
            ],
        )


class CandidateProfileModelTests(TestCase):
    """Tests for convenience helpers on CandidateProfile."""

    def setUp(self) -> None:
        recruiter = User.objects.create_user(  # type: ignore[attr-defined]
            email="pool-owner@example.com",
            password="password",
            user_type="recruiter",
            name="Owner",
        )
        self.pool = CandidatePool.objects.create(
            recruiter=recruiter, name="Spring Candidates"
        )

    def test_str_uses_candidate_name_then_title_then_fallback(self) -> None:
        """Ensure the display order prioritizes name, then title, then ID."""
        profile = CandidateProfile.objects.create(
            pool=self.pool,
            candidate_name="Jamie Example",
        )
        self.assertEqual(str(profile), "Jamie Example (Spring Candidates)")

        profile.candidate_name = ""
        profile.most_recent_title = "Staff Engineer"
        profile.save(update_fields=["candidate_name", "most_recent_title"])
        self.assertEqual(str(profile), "Staff Engineer (Spring Candidates)")

        profile.most_recent_title = ""
        profile.save(update_fields=["most_recent_title"])
        self.assertEqual(str(profile), f"Candidate {profile.pk} (Spring Candidates)")

    def test_skills_list_normalizes_whitespace(self) -> None:
        """skills_list should split on new lines and trim whitespace."""
        profile = CandidateProfile.objects.create(
            pool=self.pool,
            skills="Python\n  Django \nReact \n",
        )
        self.assertEqual(profile.skills_list, ["Python", "Django", "React"])

    def test_ideal_roles_list_handles_commas_and_spacing(self) -> None:
        """ideal_roles_list should split comma-delimited values cleanly."""
        profile = CandidateProfile.objects.create(
            pool=self.pool,
            ideal_roles=" Platform Engineer ,   SRE ,",
        )
        self.assertEqual(profile.ideal_roles_list, ["Platform Engineer", "SRE"])

    def test_display_name_and_avatar_initials(self) -> None:
        """Derived helpers should fallback gracefully when data missing."""
        profile = CandidateProfile.objects.create(
            pool=self.pool,
            candidate_name="Kai Example",
        )
        self.assertEqual(profile.display_name, "Kai Example")
        self.assertEqual(profile.avatar_initials, "KE")

        profile.candidate_name = ""
        profile.most_recent_title = "Senior Developer Advocate"
        profile.save(update_fields=["candidate_name", "most_recent_title"])
        self.assertEqual(profile.display_name, "Senior Developer Advocate")
        self.assertEqual(profile.avatar_initials, "SA")

        profile.most_recent_title = ""
        profile.save(update_fields=["most_recent_title"])
        self.assertEqual(profile.display_name, f"Candidate {profile.pk}")
        self.assertEqual(profile.avatar_initials, "CP")

class CandidateRoleRecommendationModelTests(TestCase):
    """Ensure the recommendation model mirrors expected behavior."""

    def setUp(self) -> None:
        recruiter = User.objects.create_user(  # type: ignore[attr-defined]
            email="recommender@example.com",
            password="password",
            user_type="recruiter",
            name="Recruiter",
        )
        self.pool = CandidatePool.objects.create(
            recruiter=recruiter,
            name="Summer Candidates",
        )
        self.profile = CandidateProfile.objects.create(
            pool=self.pool,
            candidate_name="Jordan Example",
        )

    def test_str_contains_role_and_pool(self) -> None:
        """__str__ should include the role title and candidate identifier."""
        rec = CandidateRoleRecommendation.objects.create(
            candidate_profile=self.profile,
            role_title="Principal Engineer",
            description="Lead complex technical initiatives.",
        )
        rendered = str(rec)
        self.assertIn("Principal Engineer", rendered)
        self.assertIn("Summer Candidates", rendered)

    def test_pool_property_returns_related_pool(self) -> None:
        """pool helper should surface candidate pool from the profile."""
        rec = CandidateRoleRecommendation.objects.create(
            candidate_profile=self.profile,
            role_title="Staff Engineer",
            description="Deep expertise role",
        )
        self.assertEqual(rec.pool, self.pool)
