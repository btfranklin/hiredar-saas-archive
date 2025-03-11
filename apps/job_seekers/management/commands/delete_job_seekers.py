"""
Management command to delete all job seeker users.

Usage:
    python manage.py delete_job_seekers
"""

import logging
import traceback

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Prefetch

from apps.authentication.models import User
from apps.job_seekers.models import JobSeekerProfile

# Setup logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Delete all job seeker users and their associated data"

    def add_arguments(self, parser):
        # Add a --force option to skip confirmation
        parser.add_argument(
            "--force",
            action="store_true",
            help="Skip confirmation prompt",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Delete ALL users (not just test users)",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)
        delete_all = options.get("all", False)
        verbosity = options.get("verbosity", 1)

        # Create the user queryset based on filters
        queryset = User.objects.filter(user_type="job_seeker")

        # By default, only delete test users (those created for testing)
        if not delete_all:
            queryset = queryset.filter(email__startswith="test_user_")
            self.stdout.write(
                self.style.WARNING(
                    "Only deleting test users (email starts with 'test_user_'). "
                    "Use --all to delete all job seekers."
                )
            )

        # Count users and related data
        users_count = queryset.count()
        if verbosity >= 2:
            # Prefetch profiles for counting associated data
            queryset = queryset.prefetch_related(
                Prefetch("job_seeker_profile", queryset=JobSeekerProfile.objects.all())
            )

            # Get more detailed counts if in verbose mode
            profiles_count = sum(
                1 for user in queryset if hasattr(user, "job_seeker_profile")
            )
        else:
            profiles_count = None

        # Exit if no users found
        if users_count == 0:
            self.stdout.write(self.style.SUCCESS("No job seeker users to delete."))
            return

        # Confirm deletion unless --force is specified
        if not force:
            target_type = "ALL" if delete_all else "TEST"
            confirm_message = f"You are about to delete {users_count} {target_type} job seeker user(s)"
            if profiles_count is not None:
                confirm_message += f" and {profiles_count} associated profile(s)"
            confirm_message += ". Are you sure? [y/N]: "

            confirm = input(confirm_message)
            if confirm.lower() not in ("y", "yes"):
                self.stdout.write(self.style.WARNING("Operation cancelled."))
                return

        # Delete users (should cascade to profiles and other related data)
        try:
            with transaction.atomic():
                # Keep track of the IDs for logging
                if verbosity >= 2:
                    user_ids = list(queryset.values_list("id", flat=True))

                # Delete the users
                deleted_count, details = queryset.delete()

                # Extract the specific counts for different models
                users_deleted = details.get("authentication.User", 0)
                profiles_deleted = details.get("job_seekers.JobSeekerProfile", 0)

                # Show detailed success message
                if verbosity >= 1:
                    deletion_details = f"Deleted {users_deleted} job seeker user(s)"
                    if verbosity >= 2:
                        deletion_details += f" and {profiles_deleted} profile(s)"
                        # Add additional detail about other deleted objects
                        for model, count in details.items():
                            if (
                                model
                                not in (
                                    "authentication.User",
                                    "job_seekers.JobSeekerProfile",
                                )
                                and count > 0
                            ):
                                model_name = model.split(".")[-1]
                                deletion_details += f", {count} {model_name}"

                    self.stdout.write(self.style.SUCCESS(deletion_details))

                # Show detailed log of deleted user IDs in very verbose mode
                if verbosity >= 3:
                    self.stdout.write(
                        "Deleted user IDs: " + ", ".join(str(uid) for uid in user_ids)
                    )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error deleting users: {str(e)}"))
            if verbosity >= 2:
                traceback.print_exc()
            raise CommandError("Failed to delete job seeker users") from e
