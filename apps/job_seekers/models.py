from django.db import models

from apps.authentication.models import User


class JobSeekerProfile(models.Model):
    """Extended profile for job seekers"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="job_seeker_profile",
        limit_choices_to={"user_type": "job_seeker"},
    )
    skills = models.TextField(blank=True, help_text="Comma-separated list of skills")
    experience = models.TextField(null=True, blank=True)
    years_of_experience = models.PositiveIntegerField(null=True, blank=True)
    desired_role = models.CharField(max_length=100, null=True, blank=True)
    current_position = models.CharField(max_length=100, null=True, blank=True)
    professional_summary = models.TextField(
        null=True,
        blank=True,
        help_text="Professional summary highlighting experience and qualifications",
    )
    resume_xml = models.TextField(
        null=True, blank=True, help_text="XML representation of the parsed resume"
    )

    # Social links
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)

    def __str__(self) -> str:
        return f"Job Seeker: {self.user.email}"

    @property
    def skills_list(self) -> list[str]:
        """Return a list of skill names"""
        if not self.skills:
            return []
        return [skill.strip() for skill in self.skills.split(",") if skill.strip()]

    def get_matched_skills_count(self, required_skills: list[str]) -> dict[str, int]:
        """
        Calculate how many of the required skills this job seeker has.

        Args:
            required_skills: List of required skill names

        Returns:
            Dictionary with matched and total skill counts
        """
        if not required_skills:
            return {"matched": 0, "total": 0}

        skills_list = self.skills_list
        matched = sum(
            1
            for skill in required_skills
            if skill.lower() in [s.lower() for s in skills_list]
        )

        return {"matched": matched, "total": len(required_skills)}
