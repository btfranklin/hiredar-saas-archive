"""Bulk resume upload model."""

from __future__ import annotations

from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone

from apps.core.upload_validators import DEFAULT_ZIP_VALIDATORS


def default_pool_name() -> str:
    """Generate a default name for a résumé pool based on current date/time."""
    return timezone.now().strftime("%Y-%m-%d %H:%M")


class BulkResumeUpload(models.Model):
    """An uploaded named pool of many résumés."""

    name = models.CharField(
        max_length=255,
        default=default_pool_name,
        help_text="Name of this résumé pool",
    )
    recruiter = models.ForeignKey(
        "recruiters.RecruiterProfile",
        on_delete=models.CASCADE,
        related_name="bulk_resume_uploads",
    )
    zip_file = models.FileField(
        upload_to="bulk_resumes/zips/",
        help_text="ZIP archive containing résumés (PDF, DOCX, etc.)",
        validators=DEFAULT_ZIP_VALIDATORS,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed = models.BooleanField(default=False)
    total_files = models.PositiveIntegerField(default=0)
    processed_profiles = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Bulk Résumé Upload"
        verbose_name_plural = "Bulk Résumé Uploads"

    def __str__(self) -> str:
        return (
            f"CandidatePool '{self.name}' – {self.recruiter.user.email} "
            f"({self.processed_profiles}/{self.total_files})"
        )

    def delete(self, using: str | None = None, keep_parents: bool = False) -> None:
        self.zip_file.delete(save=False)
        super().delete(using=using, keep_parents=keep_parents)


@receiver(post_delete, sender=BulkResumeUpload)
def delete_bulk_resume_upload_file(
    sender, instance: BulkResumeUpload, **kwargs
) -> None:
    """Ensure the uploaded ZIP file is removed from storage."""
    instance.zip_file.delete(save=False)
