"""Celery application instance for *Hiredar*.

This follows the official Django integration pattern documented at
https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html
"""

from __future__ import annotations

import os

from celery import Celery

# ---------------------------------------------------------------------------
#  Default Django settings module – identical to manage.py and asgi/wsgi.
# ---------------------------------------------------------------------------

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hiredar.settings")


# ---------------------------------------------------------------------------
#  Celery application
# ---------------------------------------------------------------------------

celery_app = Celery("hiredar")

# Read configuration from Django settings, using the `CELERY_` namespace.
celery_app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all registered Django app configs.
celery_app.autodiscover_tasks()


# ---------------------------------------------------------------------------
#  Generic wrapper to execute a plain function *and* an optional hook/callback
# ---------------------------------------------------------------------------


@celery_app.task(name="core.run_with_hook", bind=True)  # type: ignore[misc]
def _run_with_hook(
    self, original_path: str, args: list, kwargs: dict, hook_path: str | None
):  # noqa: D401
    """Execute *original_path* then call *hook_path* with a dummy Task object.

    This provides a hook mechanism so callers do not need to change.  The
    hook receives an object with attributes: ``args``, ``result`` and
    ``success``.
    """

    import importlib
    import logging

    logger = logging.getLogger(__name__)

    def _import(path: str):
        mod_path, func_name = path.rsplit(".", 1)
        mod = importlib.import_module(mod_path)
        return getattr(mod, func_name)

    func = _import(original_path)

    success: bool = True
    try:
        result_val = func(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 – propagate but mark failure
        logger.exception("Execution of %s raised: %s", original_path, exc)
        success = False
        result_val = {"status": "error", "message": str(exc)}

    if hook_path:
        try:
            hook_func = _import(hook_path)

            class _DummyTask:  # noqa: D401 – simple namespace
                def __init__(self, args_, result_, success_):
                    self.args = list(args_)
                    self.result = result_
                    self.success = success_

            hook_func(_DummyTask(args, result_val, success))
        except Exception as exc:  # noqa: BLE001 – never fail the parent task
            logger.exception("Hook %s raised: %s", hook_path, exc)

    return result_val


@celery_app.task(bind=True)
def debug_task(self):  # type: ignore[no-self-use]
    """A simple *celery -A hiredar call debug_task.delay()* smoke-test."""

    print(f"Request: {self.request!r}")
