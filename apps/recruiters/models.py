from django.db import models

from apps.authentication.models import User


class RecruiterProfile(models.Model):
    """Extended profile for recruiters"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="recruiter_profile",
        limit_choices_to={"user_type": "recruiter"},
    )

    # Subscription status
    is_subscribed = models.BooleanField(default=False)
    subscription_tier = models.CharField(
        max_length=20,
        choices=(
            ("basic", "Basic"),
            ("professional", "Professional"),
            ("enterprise", "Enterprise"),
        ),
        default="basic",
    )

    def __str__(self) -> str:
        return f"Recruiter: {self.user.email}"


class JobOpening(models.Model):
    """Model for job openings posted by recruiters"""

    recruiter = models.ForeignKey(
        RecruiterProfile,
        on_delete=models.CASCADE,
        related_name="job_openings",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=100)
    company = models.CharField(
        max_length=255, help_text="Company offering this position", default=""
    )
    salary_min = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    salary_max = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    required_skills = models.TextField(
        blank=True, help_text="Comma-separated list of required skills"
    )
    experience_years = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.title} - {self.company}"

    @property
    def required_skills_list(self) -> list[str]:
        """Return a list of required skill names"""
        if not self.required_skills:
            return []
        return [
            skill.strip() for skill in self.required_skills.split(",") if skill.strip()
        ]
