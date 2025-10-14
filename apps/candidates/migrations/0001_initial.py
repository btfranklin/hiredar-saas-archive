"""Initial state migration for the candidates app."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Introduce CandidatePool in the candidates app without touching the DB."""

    initial = True

    dependencies = [
        ("authentication", "0006_alter_user_user_type"),
        ("job_seekers", "0011_alter_talentsheet_skills"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="CandidatePool",
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
                            "name",
                            models.CharField(
                                help_text='Label for this pool (e.g. "March 2024 Upload")',
                                max_length=255,
                            ),
                        ),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        (
                            "recruiter",
                            models.ForeignKey(
                                limit_choices_to={"user_type": "recruiter"},
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="candidate_pools",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={
                        "db_table": "job_seekers_candidatepool",
                    },
                ),
            ],
            database_operations=[],
        )
    ]
