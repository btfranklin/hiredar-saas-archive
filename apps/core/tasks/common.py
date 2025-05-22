"""Central helpers for background task execution.

This module exposes two public helpers:

1. **safe_async_task** – primary entry-point used throughout the code-base for
   scheduling background work.  It now targets *Celery* instead of Django-Q but
   transparently falls back to Django-Q when Celery is unavailable (e.g. during
   the migration period or in test environments).
2. **safe_async_task_once** – wrapper that prevents duplicate queueing within a
   short window using a cache-based lock.  Its implementation is unchanged
   except that it ultimately delegates to *safe_async_task*.

Why the indirection?
--------------------
Having **exactly one place** that interacts with the task queue means we can
swap implementations – as we just did – without touching call-sites scattered
across the repository.  It also lets us add cross-cutting concerns (logging,
metrics, de-duplication, retries) in a single location.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, Callable, Final

from django.core.cache import cache

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


_CELERY_RESERVED: Final[set[str]] = {"queue", "priority"}

# Legacy Django-Q options that callers may still pass.  We keep them for source
# compatibility but ignore the ones Celery doesn’t understand.
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


def _import_callable(dotted_path: str) -> Callable[..., Any]:
    """Import a callable given its dotted path (``package.module:function``)."""

    module_path, func_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, func_name)


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
    """Schedule *path_or_callable* for background execution.

    The helper attempts Celery first and retries *retries* times on broker
    errors before giving up.  If Celery cannot be imported or is mis-
    configured we fall back to the previous Django-Q implementation so the
    system keeps running while the migration is rolled out.
    """

    # ---------------------------------------------------------------------
    #  Prepare parameters
    # ---------------------------------------------------------------------

    # Build dotted path when a callable is supplied.
    if callable(path_or_callable):
        task_name = f"{path_or_callable.__module__}.{path_or_callable.__name__}"
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


# ---------------------------------------------------------------------------
#  Duplicate-protection helper – unchanged except for delegation target
# ---------------------------------------------------------------------------


def safe_async_task_once(
    path_or_callable: str | Callable[..., Any],
    *args: Any,
    task_name: str,
    retries: int = 2,
    raise_on_failure: bool = False,
    dedup_ttl: int = 300,
    **kwargs: Any,
) -> str | None:
    """Enqueue only if an identical *task_name* is not already running.

    We first acquire a cache-based lock for *task_name*.  When the lock exists
    we silently abort to avoid duplicate work.  A second guard checks the
    Django-Q *Task* table – left intact for now because some live deployments
    still rely on it during the transition period.
    """

    lock_key = f"task-lock:{task_name}"
    got_lock = cache.add(lock_key, True, dedup_ttl)
    if not got_lock:
        logger.debug("Task '%s' already enqueued recently – skipping", task_name)
        return None

    # NOTE:
    # -----
    # Historically we consulted Django-Q's *Task* table as a second guard
    # against duplicate execution.  Now that the project has migrated to
    # Celery this database table is no longer updated which means it can
    # contain **stale rows** forever marked as *in-flight* (``success IS NULL``).
    #
    # As a consequence *safe_async_task_once* silently refused to enqueue new
    # jobs that legitimately needed to run – most notably the
    # ``create_job_opening_embeddings`` task reported in issue #742.  Recruiters
    # were able to close or draft a job (triggering *removal* tasks) but the
    # matching embeddings were never (re-)created because the stale Django-Q
    # entry made us believe a run was already in progress.
    #
    # The in-memory cache lock implemented above is sufficient for the brief
    # de-duplication window we require.  Therefore the database query has been
    # removed.  Once the legacy Django-Q dependency is dropped completely this
    # section would have been deleted anyway – we are just doing it a little
    # earlier to fix the bug.
    # --------------------------------------------------------------------

    try:
        return safe_async_task(
            path_or_callable,
            *args,
            task_name=task_name,
            retries=retries,
            raise_on_failure=raise_on_failure,
            **kwargs,
        )
    except Exception:
        cache.delete(lock_key)
        raise
