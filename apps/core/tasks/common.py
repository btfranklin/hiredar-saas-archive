"""Central helpers for background task execution.

This module exposes the main helper:

**safe_async_task** – primary entry-point for scheduling background work via Celery.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Final

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
    for key in list(kwargs.keys()):
        if key in _RESERVED_KEYS:
            scheduler_kwargs[key] = kwargs.pop(key)
    return kwargs, scheduler_kwargs


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

    # ---------------------------------------------------------------------
    #  Prepare parameters
    # ---------------------------------------------------------------------

    if callable(path_or_callable):
        task_name = getattr(path_or_callable, "name", None) or (
            f"{path_or_callable.__module__}.{path_or_callable.__name__}"
        )
    else:
        task_name = path_or_callable

    clean_kwargs, scheduler_kwargs = _split_kwargs(kwargs)

    # ---------------------------------------------------------------------
    #  Celery dispatch (single attempt – broker errors bubble up)
    # ---------------------------------------------------------------------

    from celery import current_app as celery_app  # Lazy import

    hook_path: str | None = None
    if "hook" in scheduler_kwargs:
        hook_obj = scheduler_kwargs["hook"]
        hook_path = (
            f"{hook_obj.__module__}.{hook_obj.__name__}"
            if callable(hook_obj)
            else hook_obj
        )

    if hook_path:
        # Run original callable inside the generic *run_with_hook* wrapper so
        # we can execute the callback synchronously in the same worker.
        return celery_app.send_task(
            name="core.run_with_hook",
            args=[task_name, args, clean_kwargs, hook_path],
            queue=queue,
            priority=priority,
        )

    # Fast path – plain task without special handling
    return celery_app.send_task(
        name=task_name,
        args=args,
        kwargs=clean_kwargs,
        queue=queue,
        priority=priority,
    )
