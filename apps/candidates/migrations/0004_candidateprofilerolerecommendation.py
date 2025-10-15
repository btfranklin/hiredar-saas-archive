"""Introduce CandidateRoleRecommendation for the candidates app."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Create CandidateRoleRecommendation model."""

    dependencies = [
        ("candidates", "0003_remove_candidateprofile_salary_min"),
    ]

    operations = [
        migrations.CreateModel(
            name="CandidateRoleRecommendation",
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
                    "role_title",
                    models.CharField(
                        help_text="Title of the recommended role (e.g. 'Senior Software Engineer')",
                        max_length=100,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        help_text="Short description outlining responsibilities and value",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp indicating when the recommendation was generated",
                    ),
                ),
                (
                    "candidate_profile",
                    models.ForeignKey(
                        help_text="Candidate profile this recommendation belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="role_recommendations",
                        to="candidates.candidateprofile",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
    ]
