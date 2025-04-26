"""
Middleware for job_seekers app.

Contains middleware components for the job_seekers app.
"""

import logging

from django.conf import settings
from django.core.cache import cache

from apps.job_seekers.tasks import initialize_cleanup_once


class CleanupSchedulerMiddleware:
    """Middleware to schedule cleanup tasks after Django is fully initialized."""

    _has_run = False  # Class variable to track if scheduling has run

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only attempt to schedule on the first request
        if not CleanupSchedulerMiddleware._has_run and not getattr(
            settings, "TESTING", False
        ):
            CleanupSchedulerMiddleware._has_run = True
            try:
                # Check if another process already handled this
                if not cache.get("job_seekers_first_request_handled"):
                    initialize_cleanup_once()
                    cache.set(
                        "job_seekers_first_request_handled", True, 60 * 60
                    )  # Cache for an hour
                    logging.getLogger(__name__).info(
                        "Cleanup task scheduled via middleware"
                    )
            except Exception as e:
                logging.getLogger(__name__).error(
                    "Error scheduling cleanup task: %s", e
                )

        # Continue processing the request
        return self.get_response(request)
