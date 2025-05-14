"""Common helpers for background task execution.

This module provides :func:`safe_async_task` – a thin wrapper around
``django_q.tasks.async_task`` that improves resiliency and gives us a single
indirection point should we ever migrate to another task queue.

Usage example
-------------
>>> from apps.core.tasks import safe_async_task
>>> safe_async_task(
...     "apps.job_seekers.tasks.talent_sheet_tasks.generate_talent_sheet_task",
...     profile_id,
... )

Design considerations
---------------------
*   **Centralisation** – imports originate from ``apps.core``, preventing
    accidental circular dependencies between feature apps.
*   **Resilience** – If the broker is temporarily unavailable we swallow the
    exception after configurable retries and log a helpful stack‑trace instead
    of crashing the request thread.
*   **Future‑proofing** – By funnelling all background scheduling through this
    function we can later swap Django‑Q for Celery/RQ with minimal code churn.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Django cache for cross-process locking
from django.core.cache import cache


def safe_async_task(
    func_path: str | Callable[..., Any],
    *args: Any,
    retries: int = 2,
    raise_on_failure: bool = False,
    **kwargs: Any,
) -> str | None:
    """Schedule a Django‑Q task with basic retry / error handling.

    Parameters
    ----------
    func_path:
        Dotted path to the callable.
    *args, **kwargs:
        Arguments forwarded to :func:`django_q.tasks.async_task`.
    retries:
        How many additional attempts should be made if ``async_task`` raises.
    raise_on_failure:
        When *True* we re‑raise the exception after exhausting *retries*;
        otherwise we log and return ``None`` so the caller can degrade
        gracefully (e.g. still return an HTTP 200 to the user).
    """

    attempt = 0
    while True:
        try:
            # Lazy import of async_task to avoid early ORM loading issues
            from django_q.tasks import async_task

            return async_task(func_path, *args, **kwargs)
        except Exception:  # noqa: BLE001 – we want to catch any broker error
            attempt += 1
            logger.exception(
                "async_task failed (attempt %s/%s) for %s",
                attempt,
                retries + 1,
                func_path,
            )
            if attempt > retries:
                if raise_on_failure:
                    raise
                return None


# -----------------------------------------------------------------------------
# Deduplicated task scheduling helper
# -----------------------------------------------------------------------------


# NOTE: The function signature remains backwards-compatible; new optional
# ``dedup_ttl`` lets callers tune the lock window without adjusting every call.


def safe_async_task_once(
    func_path: str | Callable[..., Any],
    *args: Any,
    task_name: str,
    retries: int = 2,
    raise_on_failure: bool = False,
    dedup_ttl: int = 300,
    **kwargs: Any,
) -> str | None:
    """Enqueue *func_path* only if there is no unfinished task with *task_name*.

    Parameters
    ----------
    func_path:
        Dotted path to the callable.
    task_name:
        Deterministic identifier to check for duplicates in ``django_q_task``.
    *args, **kwargs:
        Forwarded to :func:`safe_async_task` when a new task is needed.

    Returns
    -------
    str | None
        The task id if a new task was queued, *None* if an identical task is
        already pending.
    """

    # ---------------------------------------------------------------------
    # Fast cross-process lock via the configured Django cache.
    # ``cache.add`` is atomic: returns *False* when the key already exists.
    # ---------------------------------------------------------------------
    lock_key = f"task-lock:{task_name}"
    got_lock = cache.add(lock_key, True, dedup_ttl)
    if not got_lock:
        logger.debug("Task '%s' already enqueued recently – skipping", task_name)
        return None

    try:
        from django_q.models import Task  # Imported lazily to avoid ORM issues

        # Secondary DB check – avoids queueing a second copy when a task is
        # currently RUNNING but the cache expired or was flushed.
        if Task.objects.filter(name=task_name, success__isnull=True).exists():
            logger.debug("Task '%s' already in progress – skipping enqueue", task_name)
            return None

    except Exception:
        # If we cannot query the Task table (e.g. migrations), fall back to normal
        logger.exception("Could not check duplicates for task '%s'", task_name)

    # No pending duplicate – schedule a new one
    try:
        return safe_async_task(
            func_path,
            *args,
            task_name=task_name,
            retries=retries,
            raise_on_failure=raise_on_failure,
            **kwargs,
        )
    except Exception:
        # Ensure the lock is cleared so we can retry later.
        cache.delete(lock_key)
        raise
