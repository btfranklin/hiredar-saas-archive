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

from django_q.tasks import async_task

logger = logging.getLogger(__name__)


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
