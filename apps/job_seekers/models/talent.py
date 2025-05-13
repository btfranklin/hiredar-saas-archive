from django.db import models

from .profile import CandidatePool


class RoleRecommendation(models.Model):
    """
    Stores AI-generated role recommendations for job seekers based on their skills and experience.
    """

    job_seeker = models.ForeignKey(
        "job_seekers.JobSeekerProfile",
        on_delete=models.CASCADE,
        related_name="role_recommendations",
        help_text="The job seeker this role recommendation is for",
    )
    role_title = models.CharField(
        max_length=100,
        help_text="The title of the recommended role, in title case (e.g., 'Senior Software Engineer')",
    )
    description = models.TextField(
        help_text="A concise description of the role, outlining key responsibilities and value proposition",
    )
    is_candidate_interested = models.BooleanField(
        default=False,
        help_text="Indicates whether the job seeker has expressed interest in this role",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this recommendation was generated",
    )

    def __str__(self) -> str:
        # Use user_owner if available, otherwise just use the job_seeker pk
        user_name = (
            self.job_seeker.user_owner.get_full_name()
            if self.job_seeker.user_owner
            else f"Profile {self.job_seeker.pk}"
        )
        return f"{self.role_title} for {user_name}"

    @property
    def candidate_pool(self) -> CandidatePool | None:
        """Access the candidate pool through the job_seeker relationship."""
        return self.job_seeker.candidate_pool if self.job_seeker else None


class TalentSheet(models.Model):
    """
    AI-generated talent sheet for job seekers in the talent pool.
    """

    job_seeker = models.OneToOneField(
        "job_seekers.JobSeekerProfile",
        on_delete=models.CASCADE,
        related_name="talent_sheet",
        help_text="The job seeker this talent sheet is for",
    )
    promotional_blurb = models.TextField(
        help_text="AI-generated promotional summary highlighting the candidate's unique value proposition"
    )
    skill_overview = models.TextField(
        help_text="Concise overview of the candidate's key skills and competencies"
    )
    ideal_roles = models.TextField(
        blank=True,
        help_text="Comma-separated list of ideal roles, populated from their interested role recommendations",
    )
    skills = models.TextField(
        blank=True,
        help_text="Pipe-separated list of skills copied from JobSeekerProfile.skills for matching purposes",
    )
    personal_tagline = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        help_text="AI-generated personal identity tagline",
    )
    salary_min = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum salary expectation",
    )
    is_published = models.BooleanField(
        default=False,
        help_text="Whether this talent sheet is published and available for matching to job openings",
    )
    qualifications = models.TextField(
        blank=True,
        default="",
        help_text="Education and certifications concatenated from JobSeekerProfile for matching purposes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        # Use user_owner if available, otherwise just use the job_seeker pk
        user_name = (
            self.job_seeker.user_owner.get_full_name()
            if self.job_seeker.user_owner
            else f"Profile {self.job_seeker.pk}"
        )
        return f"Talent Sheet: {user_name}"

    @property
    def candidate_pool(self) -> CandidatePool | None:
        """Access the candidate pool through the job_seeker relationship."""
        return self.job_seeker.candidate_pool if self.job_seeker else None

    @property
    def ideal_roles_list(self) -> list[str]:
        """Returns a list of ideal roles from the comma-separated string"""
        if not self.ideal_roles:
            return []
        return [role.strip() for role in self.ideal_roles.split(",")]
