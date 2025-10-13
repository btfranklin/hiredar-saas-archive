from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.indexes import GinIndex
from django.db import models

from apps.core.models import TaskMeta


class CandidatePool(models.Model):
    """
    Represents a pool of candidates. These may have been uploaded by a recruiter,
    or may represent the "global" pool of candidates.
    """

    recruiter = models.ForeignKey(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="candidate_pools",
        limit_choices_to={"user_type": "recruiter"},
    )
    name = models.CharField(
        max_length=255, help_text='Label for this pool (e.g. "March 2024 Upload")'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Generic relation to associated background tasks (e.g. resume processing)
    tasks = GenericRelation(TaskMeta, related_query_name="candidate_pools")

    # ------------------------------------------------------------------
    # Convenience helpers for templates (avoid complex ORM calls there)
    # ------------------------------------------------------------------

    @property
    def active_tasks(self) -> list[TaskMeta]:
        """Return unfinished TaskMeta rows related to this pool."""

        return list(
            self.tasks.filter(
                state__in=(TaskMeta.State.PENDING, TaskMeta.State.RUNNING)
            ).order_by("created_at")
        )

    @property
    def has_active_tasks(self) -> bool:
        """Return *True* when any unfinished tasks exist for this pool."""

        return bool(
            self.tasks.filter(
                state__in=(TaskMeta.State.PENDING, TaskMeta.State.RUNNING)
            ).exists()
        )

    @property
    def active_task_summary(
        self,
    ) -> list[dict[str, object]]:  # noqa: D401 – simple summary
        """Return a list of {name, count} dictionaries for unfinished tasks.

        The front-end shows **one** spinner per *name* and appends "s" when
        ``count > 1`` to keep the card compact ("Processing resumes" instead of
        dozens of duplicates).
        """

        counts: dict[str, int] = {}
        for task in self.active_tasks:
            counts[task.name] = counts.get(task.name, 0) + 1

        return [{"name": name, "count": cnt} for name, cnt in counts.items()]

    def __str__(self) -> str:
        return f"Candidate Pool: {self.name} ({self.recruiter.email})"


class JobSeekerProfile(models.Model):
    """Extended profile for job seekers"""

    user_owner = models.ForeignKey(
        "authentication.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="job_seeker_profiles",
    )
    candidate_pool = models.ForeignKey(
        CandidatePool,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="job_seeker_profiles",
    )

    skills = models.TextField(blank=True, help_text="Line-separated list of skills")
    experience = models.TextField(null=True, blank=True)
    education = models.TextField(null=True, blank=True)
    certifications = models.TextField(null=True, blank=True)
    years_of_experience = models.PositiveIntegerField(null=True, blank=True)
    desired_role = models.CharField(max_length=100, null=True, blank=True)
    most_recent_title = models.CharField(max_length=100, null=True, blank=True)
    professional_summary = models.TextField(
        null=True,
        blank=True,
        help_text="Professional summary highlighting experience and qualifications",
    )
    personal_tagline = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        help_text="AI-generated personal identity tagline",
    )
    resume_xml = models.TextField(
        null=True, blank=True, help_text="XML representation of the parsed resume"
    )
    phone = models.CharField(
        max_length=30, null=True, blank=True, help_text="Phone number"
    )
    location = models.CharField(
        max_length=100, blank=True, help_text="Job seeker's location"
    )

    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    candidate_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Parsed candidate name from resume for pool-owned profiles",
    )

    def __str__(self) -> str:
        if self.user_owner:
            return f"Job Seeker: {self.user_owner.email}"
        if self.candidate_pool:
            return f"Job Seeker (Pool: {self.candidate_pool.name})"
        return f"JobSeekerProfile {self.pk}"

    @property
    def skills_list(self) -> list[str]:
        if not self.skills:
            return []
        return [skill.strip() for skill in self.skills.splitlines() if skill.strip()]

    @property
    def in_talent_pool(self) -> bool:
        from apps.job_seekers.models import TalentSheet

        try:
            return TalentSheet.objects.filter(
                job_seeker=self, is_published=True
            ).exists()
        except Exception:
            return False

    @staticmethod
    def _initials_from_text(value: str | None) -> str:
        """Return uppercase initials for the provided text."""
        if not value:
            return ""

        parts = [part for part in value.split() if part]
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        if parts:
            return parts[0][0].upper()
        return ""

    @property
    def display_name(self) -> str:
        """Return the most appropriate display name for the profile."""
        if self.user_owner and self.user_owner.name:
            return self.user_owner.name
        if self.candidate_name:
            return self.candidate_name
        if self.most_recent_title:
            return self.most_recent_title
        if self.pk:
            return f"Candidate {self.pk}"
        return "Candidate"

    @property
    def avatar_initials(self) -> str:
        """Return initials suitable for avatar placeholders."""
        if self.user_owner:
            return self.user_owner.get_initials()

        candidate_initials = self._initials_from_text(self.candidate_name)
        if candidate_initials:
            return candidate_initials

        title_initials = self._initials_from_text(self.most_recent_title)
        if title_initials:
            return title_initials

        return "JS"

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    (
                        models.Q(user_owner__isnull=False)
                        & models.Q(candidate_pool__isnull=True)
                    )
                    | (
                        models.Q(user_owner__isnull=True)
                        & models.Q(candidate_pool__isnull=False)
                    )
                ),
                name="jobseekerprofile_owner_xor",
            )
        ]
        indexes = [
            GinIndex(
                name="jobseekerprofile_skills_trgm",
                fields=["skills"],
                opclasses=["gin_trgm_ops"],
            ),
        ]
