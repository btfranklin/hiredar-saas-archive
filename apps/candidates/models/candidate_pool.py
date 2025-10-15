"""Candidate pool model for recruiter-managed resume uploads."""

from __future__ import annotations

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models

from apps.core.models import TaskMeta


class CandidatePool(models.Model):
    """
    Represents a pool of candidates uploaded and managed by a recruiter.

    The database table name remains ``job_seekers_candidatepool`` so existing
    data continues to map to this model.
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

    tasks = GenericRelation(TaskMeta, related_query_name="candidate_pools")

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
    def active_task_summary(self) -> list[dict[str, object]]:
        """Return a list of {name, count} dictionaries for unfinished tasks."""
        counts: dict[str, int] = {}
        for task in self.active_tasks:
            counts[task.name] = counts.get(task.name, 0) + 1
        return [{"name": name, "count": cnt} for name, cnt in counts.items()]

    def __str__(self) -> str:
        return f"Candidate Pool: {self.name} ({self.recruiter.email})"

    class Meta:
        db_table = "job_seekers_candidatepool"
