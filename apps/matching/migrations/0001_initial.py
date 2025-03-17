"""
Initial migration for the matching app.

This migration creates the CandidateMatch model.
"""

from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("job_seekers", "0001_initial"),
        ("recruiters", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CandidateMatch",
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
                    "match_score",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.0"),
                        help_text="Match score between 0 and 100",
                        max_digits=5,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("accepted", "Accepted"),
                            ("rejected", "Rejected"),
                            ("withdrawn", "Withdrawn"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("is_shortlisted", models.BooleanField(default=False)),
                (
                    "match_type",
                    models.CharField(
                        choices=[("top", "Top Match"), ("wildcard", "Wildcard Match")],
                        default="top",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "job_opening",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="candidate_matches",
                        to="recruiters.jobopening",
                    ),
                ),
                (
                    "job_seeker",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="job_matches",
                        to="job_seekers.jobseekerprofile",
                    ),
                ),
            ],
        ),
    ]
