"""Create the CandidateProfile model."""

import django.db.models.deletion
from django.db import migrations, models
from django.contrib.postgres.indexes import GinIndex


class Migration(migrations.Migration):
    """Introduce the new CandidateProfile table."""

    dependencies = [
        ("candidates", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CandidateProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "candidate_name",
                    models.CharField(
                        blank=True,
                        help_text="Full name parsed from the resume or provided by a recruiter",
                        max_length=150,
                    ),
                ),
                (
                    "most_recent_title",
                    models.CharField(
                        blank=True,
                        help_text="Most recent job title extracted from the resume",
                        max_length=150,
                    ),
                ),
                (
                    "desired_role",
                    models.CharField(
                        blank=True,
                        help_text="Role or career direction the candidate is interested in",
                        max_length=150,
                    ),
                ),
                (
                    "years_of_experience",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Total years of professional experience",
                        null=True,
                    ),
                ),
                (
                    "location",
                    models.CharField(
                        blank=True,
                        help_text="Candidate location or preferred working location",
                        max_length=100,
                    ),
                ),
                (
                    "phone",
                    models.CharField(
                        blank=True,
                        help_text="Phone number if provided in the resume",
                        max_length=30,
                    ),
                ),
                ("linkedin_url", models.URLField(blank=True)),
                ("github_url", models.URLField(blank=True)),
                ("portfolio_url", models.URLField(blank=True)),
                (
                    "resume_xml",
                    models.TextField(
                        blank=True,
                        help_text="Structured XML representation of the candidate resume",
                    ),
                ),
                (
                    "skills",
                    models.TextField(
                        blank=True,
                        help_text="Line-separated list of skills extracted from the resume",
                    ),
                ),
                (
                    "experience",
                    models.TextField(
                        blank=True,
                        help_text="Detailed experience content extracted from the resume",
                    ),
                ),
                (
                    "education",
                    models.TextField(
                        blank=True,
                        help_text="Education history extracted from the resume",
                    ),
                ),
                (
                    "certifications",
                    models.TextField(
                        blank=True,
                        help_text="Certifications extracted from the resume",
                    ),
                ),
                (
                    "professional_summary",
                    models.TextField(
                        blank=True,
                        help_text="Structured summary of professional accomplishments",
                    ),
                ),
                (
                    "personal_tagline",
                    models.CharField(
                        blank=True,
                        help_text="Short AI-generated tagline introducing the candidate",
                        max_length=150,
                    ),
                ),
                (
                    "promotional_blurb",
                    models.TextField(
                        blank=True,
                        help_text="AI-generated promotional overview for recruiter-facing views",
                    ),
                ),
                (
                    "experience_overview",
                    models.TextField(
                        blank=True,
                        help_text="High-level narrative of the candidate's experience",
                    ),
                ),
                (
                    "ideal_roles",
                    models.TextField(
                        blank=True,
                        help_text="Comma-separated list of ideal roles generated from recommendations",
                    ),
                ),
                (
                    "qualifications",
                    models.TextField(
                        blank=True,
                        help_text="Combined education and certifications summary for matching",
                    ),
                ),
                (
                    "salary_min",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Minimum salary expectation if available",
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "is_published",
                    models.BooleanField(
                        default=False,
                        help_text="Whether this profile is eligible for matching workflows",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "pool",
                    models.ForeignKey(
                        help_text="Candidate pool that owns this candidate record",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="candidate_profiles",
                        to="candidates.candidatepool",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="candidateprofile",
            index=GinIndex(
                fields=["skills"],
                name="candidateprofile_skills_trgm",
                opclasses=["gin_trgm_ops"],
            ),
        ),
    ]

