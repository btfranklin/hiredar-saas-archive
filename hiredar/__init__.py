"""Project package initialisation.

Exposes the *Celery* application instance as ``hiredar.celery_app`` so that
``celery -A hiredar worker`` works out-of-the-box.
"""

# Importing *celery_app* makes it discoverable by Celery command-line tools.

from .celery import celery_app  # noqa: F401  (re-export for Celery)
