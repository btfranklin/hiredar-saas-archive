from django.db import models


class UploadedResumePool(models.Model):
    """
    Represents a batch of resumes uploaded by a recruiter.
    """

    recruiter = models.ForeignKey(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="uploaded_resume_pools",
        limit_choices_to={"user_type": "recruiter"},
    )
    name = models.CharField(
        max_length=255, help_text='Label for this pool (e.g. "March 2024 Upload")'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Resume Pool: {self.name} ({self.recruiter.email})"


class JobSeekerProfile(models.Model):
    """Extended profile for job seekers"""

    user_owner = models.ForeignKey(
        "authentication.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="job_seeker_profiles",
    )
    uploaded_resume_pool = models.ForeignKey(
        UploadedResumePool,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="job_seeker_profiles",
    )

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
        max_length=30, null=True, blank=True, help_text="Phone number"
    )
    location = models.CharField(
        max_length=100, blank=True, help_text="Job seeker's location"
    )

    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    candidate_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Parsed candidate name from resume for pool-owned profiles",
    )

    def __str__(self) -> str:
        if self.user_owner:
            return f"Job Seeker: {self.user_owner.email}"
        if self.uploaded_resume_pool:
            return f"Job Seeker (Pool: {self.uploaded_resume_pool.name})"
        return f"JobSeekerProfile {self.pk}"

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

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    (
                        models.Q(user_owner__isnull=False)
                        & models.Q(uploaded_resume_pool__isnull=True)
                    )
                    | (
                        models.Q(user_owner__isnull=True)
                        & models.Q(uploaded_resume_pool__isnull=False)
                    )
                ),
                name="jobseekerprofile_owner_xor",
            )
        ]
