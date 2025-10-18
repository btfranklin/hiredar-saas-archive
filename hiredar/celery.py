"""Celery application instance for *Hiredar*.

This follows the official Django integration pattern documented at
https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html
"""

from __future__ import annotations

import os

import celery.app.trace
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
#  Custom logging format to prevent PII exposure
# ---------------------------------------------------------------------------

# Customize Celery's logging formats to exclude return values that may contain PII
# The default LOG_SUCCESS format includes %(return_value)s which can expose
# sensitive information like candidate names and analysis content in logs.
# We remove this to prevent PII exposure while keeping task completion info.

# Custom formats that exclude potentially sensitive information
celery.app.trace.LOG_SUCCESS = """\
Task %(name)s[%(id)s] succeeded in %(runtime)ss\
"""

