from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("candidates", "0005_alter_candidateprofile_options"),
    ]

    operations = [
        migrations.RunSQL(
            "DROP TABLE IF EXISTS resume_processing_resumeprocessingtaskprogress CASCADE",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            "DROP TABLE IF EXISTS resume_processing_resumeprocessingjob CASCADE",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.CreateModel(
            name="ResumeProcessingTaskProgress",
            fields=[
                (
                    "task_id",
                    models.CharField(
                        help_text="Django Q2 task ID",
                        max_length=50,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "task_type",
                    models.CharField(
                        default="resume_processing",
                        help_text="Type of task being processed",
                        max_length=50,
                    ),
                ),
                (
                    "current_step",
                    models.CharField(
                        default="initializing",
                        help_text="Current step being processed",
                        max_length=100,
                    ),
                ),
                (
                    "progress_percent",
                    models.IntegerField(
                        default=0,
                        help_text="Overall progress percentage (0-100)",
                    ),
                ),
                (
                    "steps_completed",
                    models.TextField(
                        blank=True,
                        default="[]",
                        help_text="JSON list of completed steps",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "message",
                    models.TextField(
                        blank=True,
                        help_text="Status message or error details",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="resume_processing_progress",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "resume_processing_resumeprocessingtaskprogress",
                "verbose_name": "Resume Processing Task Progress",
                "verbose_name_plural": "Resume Processing Task Progress",
            },
        ),
        migrations.CreateModel(
            name="ResumeProcessingJob",
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
                    "processed_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the résumé processing completed",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("success", "Success"), ("failed", "Failed")],
                        default="success",
                        help_text="Result of the processing job",
                        max_length=20,
                    ),
                ),
                (
                    "candidate_profile",
                    models.ForeignKey(
                        help_text="Candidate profile that was processed",
                        on_delete=models.CASCADE,
                        related_name="processing_jobs",
                        to="candidates.candidateprofile",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="User who initiated the résumé processing",
                        on_delete=models.CASCADE,
                        related_name="resume_processing_jobs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "resume_processing_resumeprocessingjob",
                "ordering": ["-processed_at"],
                "verbose_name": "Résumé Processing Job",
                "verbose_name_plural": "Résumé Processing Jobs",
            },
        ),
    ]
