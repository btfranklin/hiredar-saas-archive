"""Core models for shared infrastructure."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class TaskMeta(models.Model):
    """Metadata row for a single long-running background task."""

    class State(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        SUCCESS = "SUCCESS", "Success"
        FAILURE = "FAILURE", "Failure"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    queue_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=120)

    state = models.CharField(
        max_length=12,
        choices=State.choices,
        default=State.PENDING,
    )
    progress = models.PositiveSmallIntegerField(null=True, blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks",
        null=True,
        blank=True,
    )

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
            models.Index(fields=["content_type", "object_id", "state"]),
        ]
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"TaskMeta(id={self.id}, name={self.name}, state={self.state})"
