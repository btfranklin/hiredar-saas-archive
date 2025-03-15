"""
Management command to list all job seeker users.

Usage:
    python manage.py list_job_seekers
"""

import logging

from django.core.management.base import BaseCommand

from apps.authentication.models import User

# Setup logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "List all job seeker users with basic information"

    def add_arguments(self, parser):
        parser.add_argument(
            "--test-only",
            action="store_true",
            help="Only list test users (email starts with 'test_user_')",
        )

    def handle(self, *args, **options):
        test_only = options.get("test_only", False)
        verbosity = options.get("verbosity", 1)

        # Build the queryset based on filters
        queryset = User.objects.filter(user_type="job_seeker")

        if test_only:
            queryset = queryset.filter(email__startswith="test_user_")
            self.stdout.write(self.style.WARNING("Listing test users only"))

        # Get the count
        users_count = queryset.count()

        if users_count == 0:
            self.stdout.write(self.style.NOTICE("No job seeker users found"))
            return

        # Order by username
        queryset = queryset.order_by("username")

        # Prefetch profiles for efficiency
        queryset = queryset.select_related("job_seeker_profile")

        # Print header
        self.stdout.write(f"Found {users_count} job seeker user(s):")
        self.stdout.write("-" * 80)

        # Define format strings based on verbosity
        if verbosity >= 2:
            # Verbose mode shows more columns
            format_str = "{id:<6} {name:<25} {username:<30} {email:<30} {title}"
            # Print column headers
            self.stdout.write(
                format_str.format(
                    id="ID",
                    name="Name",
                    username="Username",
                    email="Email",
                    title="Current Position",
                )
            )
        else:
            # Default mode shows just name and username
            format_str = "{id:<6} {name:<25} {username:<48}"
            # Print column headers
            self.stdout.write(
                format_str.format(id="ID", name="Name", username="Username")
            )

        self.stdout.write("-" * 80)

        # Print each user's info
        for user in queryset:
            # Try to get the profile info
            profile = getattr(user, "job_seeker_profile", None)
            position = getattr(profile, "most_recent_title", "") if profile else ""

            # Format the name
            name = f"{user.name}".strip()
            if not name:
                name = "(No name)"

            # Truncate fields that are too long
            name_display = name[:23] + ".." if len(name) > 23 else name
            username_display = user.username

            if verbosity >= 2:
                # In verbose mode, truncate all fields to fit the format
                username_display = (
                    user.username[:28] + ".."
                    if len(user.username) > 28
                    else user.username
                )
                email_display = (
                    user.email[:28] + ".." if len(user.email) > 28 else user.email
                )
                position_display = (
                    position[:30] + ".." if len(str(position)) > 30 else position
                )

                # Print user info with all fields
                self.stdout.write(
                    format_str.format(
                        id=str(user.pk),
                        name=name_display,
                        username=username_display,
                        email=email_display,
                        title=position_display,
                    )
                )
            else:
                # In default mode, allow username to use more space
                username_display = (
                    user.username[:46] + ".."
                    if len(user.username) > 46
                    else user.username
                )

                # Print user info with limited fields
                self.stdout.write(
                    format_str.format(
                        id=str(user.pk), name=name_display, username=username_display
                    )
                )

            # Print additional details in verbose mode
            if verbosity >= 2 and profile:
                if profile.years_of_experience:
                    self.stdout.write(
                        f"    Experience: {profile.years_of_experience} years"
                    )

                if profile.skills:
                    skills = profile.skills_list
                    if skills:
                        if len(skills) > 5:
                            skills_display = (
                                ", ".join(skills[:5]) + f" (+{len(skills)-5} more)"
                            )
                        else:
                            skills_display = ", ".join(skills)
                        self.stdout.write(f"    Skills: {skills_display}")

                # Add a blank line for readability in verbose mode
                self.stdout.write("")

        self.stdout.write("-" * 80)
