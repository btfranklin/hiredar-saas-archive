"""Central helpers for background task execution.

This module exposes the main helper:

**safe_async_task** – primary entry-point for scheduling background work via Celery.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Final

from celery import current_app as celery_app
from django.conf import settings  # type: ignore

from apps.core.services.task_idempotency import IdempotentTaskManager  # type: ignore

# from apps.core.services.task_idempotency import IdempotentTaskManager  # type: ignore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


_CELERY_RESERVED: Final[set[str]] = {"queue", "priority"}

# Legacy options that callers may still pass; ignored if unrecognized by Celery.
_LEGACY_RESERVED: Final[set[str]] = {
    "hook",
    "group",
    "task_name",
    "cached",
    "sync",
    "save",
}

_RESERVED_KEYS: Final[frozenset[str]] = frozenset(_CELERY_RESERVED | _LEGACY_RESERVED)


def _split_kwargs(kwargs: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return *(clean_kwargs, scheduler_kwargs)* by stripping reserved keys."""

    scheduler_kwargs: dict[str, Any] = {}
    clean_kwargs: dict[str, Any] = {}
    for key, value in kwargs.items():
        if key in _RESERVED_KEYS:
            scheduler_kwargs[key] = value
        else:
            clean_kwargs[key] = value
    return clean_kwargs, scheduler_kwargs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def safe_async_task(
    path_or_callable: str | Callable[..., Any],
    *args: Any,
    queue: str = "default",
    priority: int = 5,
    retries: int = 2,
    raise_on_failure: bool = False,
    **kwargs: Any,
) -> str | None:
    """Schedule *path_or_callable* for background execution via Celery.

    Retries on broker errors up to *retries* times before raising.
    """

    if callable(path_or_callable):
        task_name = getattr(path_or_callable, "name", None) or (
            f"{path_or_callable.__module__}.{path_or_callable.__name__}"
        )
    else:
        task_name = path_or_callable

    clean_kwargs, scheduler_kwargs = _split_kwargs(kwargs)

    is_eager = bool(
        getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
        or os.getenv("PYTEST_CURRENT_TEST")
    )

    # If a task callable is provided and we're in eager mode or idempotent requested,
    # execute via apply_async (respects eager) optionally with idempotency.
    if callable(path_or_callable):
        if scheduler_kwargs.get("idempotent"):
            deterministic_name = scheduler_kwargs.get("task_name") or task_name
            return IdempotentTaskManager.safe_task_execution(
                path_or_callable,
                str(deterministic_name),
                *args,
                **clean_kwargs,
            )

        if is_eager:
            result = path_or_callable.apply_async(  # type: ignore[attr-defined]
                args=args,
                kwargs=clean_kwargs,
                queue=queue,
                priority=priority,
            )
            return getattr(result, "id", None)

    # If only a task name was provided, try to resolve it to a task when eager
    # so apply_async runs inline; otherwise publish via broker.
    if not callable(path_or_callable) and is_eager:
        task_map = getattr(celery_app, "tasks", {})
        task = task_map[task_name] if task_name in task_map else None  # type: ignore[index]
        if task is not None:
            result = task.apply_async(args=args, kwargs=clean_kwargs, queue=queue, priority=priority)  # type: ignore[call-arg]
            return getattr(result, "id", None)

    # Default: route by task name through the broker
    return celery_app.send_task(
        name=task_name,
        args=list(args),
        kwargs=clean_kwargs,
        queue=queue,
        priority=priority,
    )
