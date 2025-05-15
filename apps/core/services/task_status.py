"""Helpers for querying task progress for the front-end.

These functions are intentionally *thin* wrappers around simple ORM queries so
that they stay backend-agnostic. If you later switch from Django-Q to Celery or
another queue you only need to keep updating the *producers* of the
``TaskMeta`` rows—these helpers require no changes.
"""

from __future__ import annotations

from apps.core.models import TaskMeta

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def _tasks_for_object(obj) -> list[TaskMeta]:
    """Return unfinished TaskMeta rows for an arbitrary model instance."""

    return list(
        obj.tasks.filter(state__in={"PENDING", "RUNNING"}).order_by("created_at")  # type: ignore[attr-defined]
    )


def summarize_tasks(tasks: list[TaskMeta]) -> dict:
    """Return a dict that the front-end can easily JSON-serialize.

    American spelling of *summarize* is intentional per project guidelines.
    """

    return {
        "count": len(tasks),
        "items": [
            {
                "name": task.name,
                "state": task.state,
                "progress": task.progress,
            }
            for task in tasks
        ],
    }


def active_tasks_for_pool(pool_id: int) -> list[TaskMeta]:
    """Return unfinished TaskMeta rows for the given candidate-pool ID.

    Internally maps the legacy arguments to the generic ownership fields.
    """

    from apps.job_seekers.models import (
        CandidatePool,  # local import to avoid hard dependency
    )

    pool = CandidatePool.objects.filter(pk=pool_id).first()
    if not pool:
        return []
    return _tasks_for_object(pool)
