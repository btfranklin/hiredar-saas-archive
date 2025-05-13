"""
Management command to inspect job seeker profiles and talent sheets.

This command displays detailed information about a job seeker when provided with their name.
"""

from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.authentication.models import User
from apps.job_seekers.models import JobSeekerProfile, TalentSheet


class Command(BaseCommand):
    """Display detailed information about a job seeker and their talent sheet."""

    help = "Display detailed information about a job seeker and their talent sheet."

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "name",
            type=str,
            help="Name of the job seeker to inspect (partial match is supported)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the command."""
        name = options["name"]
        self.stdout.write(f"Searching for job seeker with name containing: {name}")

        # Find the user by name
        users = User.objects.filter(
            Q(name__icontains=name) & Q(user_type="job_seeker")
        ).order_by("name")

        if not users.exists():
            self.stdout.write(
                self.style.ERROR(f"No job seekers found with name containing '{name}'")
            )
            return

        # If multiple users match, list them and allow the user to select one
        if users.count() > 1:
            self.stdout.write(
                self.style.WARNING(
                    f"Found {users.count()} job seekers with name containing '{name}'"
                )
            )
            self.stdout.write("Please refine your search or select from the list:")
            for i, user in enumerate(users):
                self.stdout.write(f"{i+1}. {user.name} ({user.email})")  # type: ignore[attr-defined]
            return

        # Get the user (users.exists() verified above)
        user = users.first()
        if user is None:  # Safety check for static analysis
            self.stdout.write(
                self.style.ERROR("Unexpected error: User object was None")
            )
            return
        self.stdout.write(
            self.style.SUCCESS(f"Found job seeker: {user.name} ({user.email})")  # type: ignore[attr-defined]
        )

        # Check if user has a job seeker profile
        try:
            profile = user.job_seeker_profile  # type: ignore[attr-defined]
        except JobSeekerProfile.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Job seeker {user.name} does not have a profile")  # type: ignore[attr-defined]
            )
            return

        # Display profile information
        self.stdout.write("\n=== Job Seeker Profile ===")
        self.stdout.write(f"ID: {profile.id}")
        self.stdout.write(
            f"Most Recent Title: {profile.most_recent_title or 'Not set'}"
        )
        self.stdout.write(
            f"Years of Experience: {profile.years_of_experience or 'Not set'}"
        )
        self.stdout.write(f"Desired Role: {profile.desired_role or 'Not set'}")
        self.stdout.write(f"Location: {profile.location or 'Not set'}")

        # Display skills
        if profile.skills:
            self.stdout.write("\nSkills:")
            for skill in profile.skills_list:
                self.stdout.write(f"  - {skill}")
        else:
            self.stdout.write("\nSkills: None specified")

        # Display professional summary
        if profile.professional_summary:
            self.stdout.write("\nProfessional Summary:")
            self.stdout.write(f"  {profile.professional_summary}")

        # Check if user has a talent sheet
        try:
            talent_sheet = profile.talent_sheet
            self.stdout.write("\n=== Talent Sheet ===")
            self.stdout.write(f"ID: {talent_sheet.id}")
            self.stdout.write(
                f"Published: {'Yes' if talent_sheet.is_published else 'No'}"
            )
            self.stdout.write(f"Created: {talent_sheet.created_at}")
            self.stdout.write(f"Updated: {talent_sheet.updated_at}")

            # Display talent sheet details
            self.stdout.write("\nPromotional Blurb:")
            self.stdout.write(f"  {talent_sheet.promotional_blurb}")

            self.stdout.write("\nExperience Overview:")
            self.stdout.write(f"  {talent_sheet.experience_overview}")

            if talent_sheet.ideal_roles:
                self.stdout.write("\nIdeal Roles:")
                for role in talent_sheet.ideal_roles_list:
                    self.stdout.write(f"  - {role}")
            else:
                self.stdout.write("\nIdeal Roles: None specified")

            if talent_sheet.salary_min:
                self.stdout.write(f"\nMinimum Salary: ${talent_sheet.salary_min}")

        except TalentSheet.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(
                    f"Job seeker {user.name} does not have a talent sheet"  # type: ignore[attr-defined]
                )
            )
