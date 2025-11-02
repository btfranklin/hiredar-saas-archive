"""
Models used to track simple page view counts.
"""

from __future__ import annotations

from django.db import models


class PageViewCount(models.Model):
    """
    Tracks the number of GET requests made to a given path.
    """

    path = models.CharField(max_length=512, unique=True)
    view_count = models.PositiveBigIntegerField(default=0)
    first_viewed_at = models.DateTimeField(auto_now_add=True)
    last_viewed_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-view_count", "path"]
        verbose_name = "Page view count"
        verbose_name_plural = "Page view counts"

    def __str__(self) -> str:
        return f"{self.path} ({self.view_count})"
