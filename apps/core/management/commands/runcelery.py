"""
Management command to run Celery worker with predefined parameters.

This command starts a Celery worker with beat scheduler using the exact
parameters needed for the hiredar application.
"""

import os
import subprocess
import sys

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Run Celery worker with predefined parameters."""

    help = "Start Celery worker with beat scheduler using predefined parameters"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show the command that would be executed without running it",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        # The exact command parameters the user requested
        # Build Celery command with proper option ordering: global opts before subcommand
        celery_command = [
            "pdm",
            "run",
            "celery",
            "--app",
            "hiredar",
        ]

        # Ensure the worker uses the exact broker URL from Django settings (global option)
        broker_url = getattr(settings, "CELERY_BROKER_URL", None)
        if broker_url:
            celery_command.extend(["--broker", broker_url])

        # Subcommand and worker options
        celery_command.extend(
            [
                "worker",
                "--beat",
                "--loglevel",
                "info",
                "--queues",
                "default,high",
                "--concurrency",
                os.getenv("CELERY_CONCURRENCY", "2"),
                "--optimization",
                "fair",
                "--max-tasks-per-child",
                os.getenv("CELERY_MAX_TASKS_PER_CHILD", "20"),
            ]
        )

        if options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(f"Would execute: {' '.join(celery_command)}")
            )
            return

        try:
            self.stdout.write(
                self.style.SUCCESS("Starting Celery worker with beat scheduler...")
            )
            self.stdout.write(f"Command: {' '.join(celery_command)}")

            # Execute the celery command
            subprocess.run(celery_command, check=True)

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nCelery worker stopped by user."))
        except subprocess.CalledProcessError as e:
            self.stdout.write(
                self.style.ERROR(f"Celery worker failed with exit code {e.returncode}")
            )
            sys.exit(e.returncode)
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(
                    "Could not find 'pdm' command. Make sure PDM is installed and in your PATH."
                )
            )
            sys.exit(1)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Unexpected error: {e}"))
            sys.exit(1)
