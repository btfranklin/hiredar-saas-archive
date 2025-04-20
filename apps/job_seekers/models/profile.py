from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.authentication.models import User


class UploadedResumePool(models.Model):
    """
    Represents a batch of resumes uploaded by a recruiter for a specific job opening.
    """

    recruiter = models.ForeignKey(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="uploaded_resume_pools",
        limit_choices_to={"user_type": "recruiter"},
    )
    job_opening = models.ForeignKey(
        "recruiters.JobOpening",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_resume_pools",
        help_text="Job opening associated with this pool (optional, non-ownership)",
    )
    name = models.CharField(
        max_length=255, help_text='Label for this pool (e.g. "March 2024 Upload")'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Resume Pool: {self.name} ({self.recruiter.email})"


class JobSeekerProfile(models.Model):
    """Extended profile for job seekers (now supports polymorphic owner)"""

    # Polymorphic owner: can be User or UploadedResumePool
    owner_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    owner_object_id = models.PositiveIntegerField(null=True, blank=True)
    owner = GenericForeignKey("owner_content_type", "owner_object_id")

    skills = models.TextField(blank=True, help_text="Pipe-separated list of skills")
    experience = models.TextField(null=True, blank=True)
    education = models.TextField(null=True, blank=True)
    certifications = models.TextField(null=True, blank=True)
    years_of_experience = models.PositiveIntegerField(null=True, blank=True)
    desired_role = models.CharField(max_length=100, null=True, blank=True)
    most_recent_title = models.CharField(max_length=100, null=True, blank=True)
    professional_summary = models.TextField(
        null=True,
        blank=True,
        help_text="Professional summary highlighting experience and qualifications",
    )
    personal_tagline = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        help_text="AI-generated personal identity tagline",
    )
    resume_xml = models.TextField(
        null=True, blank=True, help_text="XML representation of the parsed resume"
    )
    phone = models.CharField(
        max_length=20, null=True, blank=True, help_text="Phone number"
    )
    location = models.CharField(
        max_length=100, blank=True, help_text="Job seeker's location"
    )

    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)

    def __str__(self) -> str:
        if self.user_owner:
            return f"Job Seeker: {self.user_owner.email}"
        if self.uploaded_resume_pool:
            return f"Job Seeker (Pool: {self.uploaded_resume_pool.name})"
        return f"JobSeekerProfile {self.pk}"

    @property
    def uploaded_resume_pool(self) -> UploadedResumePool | None:
        if isinstance(self.owner, UploadedResumePool):
            return self.owner
        return None

    @property
    def user_owner(self) -> User | None:
        if isinstance(self.owner, User):
            return self.owner
        return None

    @property
    def skills_list(self) -> list[str]:
        if not self.skills:
            return []
        return [skill.strip() for skill in self.skills.split("|") if skill.strip()]

    @property
    def in_talent_pool(self) -> bool:
        from apps.job_seekers.models import TalentSheet

        try:
            return TalentSheet.objects.filter(
                job_seeker=self, is_published=True
            ).exists()
        except Exception:
            return False
