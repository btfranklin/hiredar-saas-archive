"""Core app models.

This module currently hosts only the ``TaskMeta`` model which stores lightweight
metadata about asynchronous tasks that the front-end may need to poll for
progress.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

# NOTE: This model intentionally avoids *any* direct import of domain models
# (e.g. ``CandidatePool``) to keep the ``core`` app decoupled. Ownership is
# expressed via a ``GenericForeignKey`` instead.


class TaskMeta(models.Model):
    """Metadata row for a single long-running background task.

    The record is deliberately *thin*: it stores only the information that the
    user interface needs to display progress and decide whether to continue
    polling.
    """

    class State(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        SUCCESS = "SUCCESS", "Success"
        FAILURE = "FAILURE", "Failure"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # The identifier returned by the queue backend (Celery, Django-Q, …)
    queue_id = models.CharField(max_length=50, unique=True)
    # Short human-readable description used directly in the UI
    name = models.CharField(max_length=120)

    state = models.CharField(
        max_length=12,
        choices=State.choices,
        default=State.PENDING,
    )
    # 0-100 percentage progress where applicable
    progress = models.PositiveSmallIntegerField(null=True, blank=True)

    # Optional owner – handy when we need to show *all* tasks for a user
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks",
        null=True,
        blank=True,
    )

    # Generic ownership – allows *any* model instance to own tasks while keeping
    # this core app independent of specific domain objects such as
    # ``CandidatePool``.
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            # Fast lookup of unfinished work for owner objects and state
            models.Index(fields=["content_type", "object_id", "state"]),
        ]
        ordering = ["created_at"]

    # ---------------------------------------------------------------------
    # Dunder methods
    # ---------------------------------------------------------------------
    def __str__(self) -> str:  # noqa: D401 – simple verb form is fine
        return f"TaskMeta(id={self.id}, name={self.name}, state={self.state})"
