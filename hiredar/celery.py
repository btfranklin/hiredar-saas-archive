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
#  Legacy Django-Q style task registration removed (now fully Celery-native)
# ---------------------------------------------------------------------------
#
# The existing code-base still defines many background jobs as **plain Python
# functions** (some decorated with the old ``django_q2.task`` helper).  Celery
# only recognises callables that are explicitly registered.  To avoid having to
# touch every module during the migration we scan the ``*.tasks`` packages of
# all installed Django apps *after* autodiscovery and programmatically register
# every callable exported via their ``__all__`` attribute.
#
# This keeps the public contract unchanged: callers schedule tasks via
# ``safe_async_task(<callable>)`` by passing either the function object or its
# dotted path.  Celery will now be able to locate and execute them because we
# created shim tasks at start-up that simply import-and-delegate.
# ---------------------------------------------------------------------------


def _register_legacy_tasks() -> None:  # pragma: no cover – startup helper
    """Register shim Celery tasks for legacy plain functions.

    Any callable exported by package.tasks via __all__ becomes a Celery
    task whose name equals its dotted path, matching the convention used by
    apps.core.tasks.common.safe_async_task."""


    import importlib
    import logging

    from django.apps import apps as django_apps

    logger = logging.getLogger(__name__)

    for app_config in django_apps.get_app_configs():
        try:
            tasks_mod = importlib.import_module(f"{app_config.name}.tasks")
        except ModuleNotFoundError:
            # App has no tasks package – perfectly fine.
            continue

        public_names = getattr(tasks_mod, "__all__", [])
        for name in public_names:
            attr = getattr(tasks_mod, name, None)
            if not callable(attr):  # pragma: no mutate – skip constants, etc.
                continue

            # Two canonical names need to be recognised:
            #   • the re-exported path (apps.<app>.tasks.<func>) that callers might
            #     use via explicit string or dotted-path import *when the func is
            #     referenced through the package level*.
            #   • the *origin* path where the function is defined
            #     (e.g. apps.<app>.tasks.bulk_resume_tasks.<func>) which is what we
            #     get when the callable object itself is passed to
            #     safe_async_task.

            candidate_names: list[str] = [f"{tasks_mod.__name__}.{name}"]

            origin_name = f"{attr.__module__}.{attr.__name__}"
            if origin_name not in candidate_names:
                candidate_names.append(origin_name)

            def _make_shim(func, task_name: str):  # noqa: D401 – tiny helper
                """Register a Celery shim task named *task_name*."""

                if task_name in celery_app.tasks:  # type: ignore[attr-defined]
                    return  # already present – skip

                @celery_app.task(name=task_name, bind=True)  # type: ignore[misc]
                def _shim(self, *args, **kwargs):  # noqa: ANN001
                    return func(*args, **kwargs)

                logger.debug("Registered legacy task shim for %s", task_name)

            for _task_name in candidate_names:
                _make_shim(attr, _task_name)


# Django must be fully initialised so that get_app_configs() works.
import django  # noqa: E402, WPS433 – runtime dependency

django.setup()
_register_legacy_tasks()


# ---------------------------------------------------------------------------
#  Generic wrapper to execute a plain function *and* an optional hook/callback
# ---------------------------------------------------------------------------


@celery_app.task(name="core.run_with_hook", bind=True)  # type: ignore[misc]
def _run_with_hook(self, original_path: str, args: list, kwargs: dict, hook_path: str | None):  # noqa: D401
    """Execute *original_path* then call *hook_path* with a dummy Task object.

    This re-implements the old **django_q** "hook=" feature so callers do not
    need to change.  The hook receives an object that mimics the relevant
    attributes of Django-Qʼs *Task* model: ``args``, ``result`` and
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
