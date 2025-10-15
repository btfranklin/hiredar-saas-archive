from django.db import models

from apps.authentication.models import User
from apps.candidates.models import CandidateProfile


class ResumeProcessingJob(models.Model):
    """
    Tracks a single resume processing event for quota enforcement.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="resume_processing_jobs",
        help_text="User who initiated the resume processing",
    )
    candidate_profile = models.ForeignKey(
        CandidateProfile,
        on_delete=models.CASCADE,
        related_name="processing_jobs",
        help_text="Candidate profile that was processed",
    )
    processed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the resume processing completed",
    )
    status = models.CharField(
        max_length=20,
        choices=[("success", "Success"), ("failed", "Failed")],
        default="success",
        help_text="Result of the processing job",
    )

    class Meta:
        ordering = ["-processed_at"]
        verbose_name = "Resume Processing Job"
        verbose_name_plural = "Resume Processing Jobs"

    def __str__(self) -> str:
        return f"Job {self.pk} by {self.user.email} at {self.processed_at}"
