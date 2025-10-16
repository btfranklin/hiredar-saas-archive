"""Resume file model."""

from __future__ import annotations

from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.core.upload_validators import DEFAULT_RESUME_VALIDATORS


class ResumeFile(models.Model):
    """Individual PDF resume extracted from a named pool."""

    bulk_upload = models.ForeignKey(
        "recruiters.BulkResumeUpload",
        on_delete=models.CASCADE,
        related_name="resume_files",
    )
    recruiter = models.ForeignKey(
        "recruiters.RecruiterProfile",
        on_delete=models.CASCADE,
        related_name="resume_files",
    )
    file = models.FileField(
        upload_to="bulk_resumes/items/",
        validators=DEFAULT_RESUME_VALIDATORS,
    )
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Résumé File"
        verbose_name_plural = "Résumé Files"
        unique_together = ["bulk_upload", "original_filename"]

    def __str__(self) -> str:
        return f"{self.original_filename}"

    def delete(self, using: str | None = None, keep_parents: bool = False) -> None:
        self.file.delete(save=False)
        super().delete(using=using, keep_parents=keep_parents)


@receiver(post_delete, sender=ResumeFile)
def delete_resume_file_file(sender, instance: ResumeFile, **kwargs) -> None:
    """Ensure the stored resume PDF is deleted with the model."""
    instance.file.delete(save=False)
