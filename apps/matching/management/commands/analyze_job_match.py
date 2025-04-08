"""
Management command to analyze matching between a job seeker and job opening.

This command displays detailed information about the match or lack of match between
a specified job seeker and job opening.
"""

import json
from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.authentication.models import User
from apps.job_seekers.models import JobSeekerProfile, TalentSheet
from apps.matching.models import CandidateMatch
from apps.recruiters.models import JobOpening


class Command(BaseCommand):
    """Analyze matching between a job seeker and job opening."""

    help = "Analyze why a job seeker is or isn't matching with a job opening."

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "job_seeker_name",
            type=str,
            help="Name of the job seeker to analyze (partial match is supported)",
        )
        parser.add_argument(
            "job_title",
            type=str,
            help="Title of the job opening to analyze (partial match is supported)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the command."""
        job_seeker_name = options["job_seeker_name"]
        job_title = options["job_title"]

        self.stdout.write(
            f"Analyzing matching for job seeker '{job_seeker_name}' and job opening '{job_title}'"
        )

        # Find the job seeker by name
        users = User.objects.filter(
            Q(name__icontains=job_seeker_name) & Q(user_type="job_seeker")
        ).order_by("name")

        if not users.exists():
            self.stdout.write(
                self.style.ERROR(
                    f"No job seekers found with name containing '{job_seeker_name}'"
                )
            )
            return

        # If multiple users match, list them and exit
        if users.count() > 1:
            self.stdout.write(
                self.style.WARNING(
                    f"Found {users.count()} job seekers with name containing '{job_seeker_name}'"
                )
            )
            self.stdout.write("Please refine your search or select from the list:")
            for i, user in enumerate(users):
                self.stdout.write(f"{i+1}. {user.name} ({user.email})")
            return

        # Get the user
        user = users.first()
        self.stdout.write(
            self.style.SUCCESS(f"Found job seeker: {user.name} ({user.email})")
        )

        # Find the job opening by title
        job_openings = JobOpening.objects.filter(title__icontains=job_title).order_by(
            "title"
        )

        if not job_openings.exists():
            self.stdout.write(
                self.style.ERROR(
                    f"No job openings found with title containing '{job_title}'"
                )
            )
            return

        # If multiple job openings match, list them and exit
        if job_openings.count() > 1:
            self.stdout.write(
                self.style.WARNING(
                    f"Found {job_openings.count()} job openings with title containing '{job_title}'"
                )
            )
            self.stdout.write("Please refine your search or select from the list:")
            for i, job in enumerate(job_openings):
                self.stdout.write(f"{i+1}. {job.title} - {job.company}")
            return

        # Get the job opening
        job_opening = job_openings.first()
        self.stdout.write(
            self.style.SUCCESS(
                f"Found job opening: {job_opening.title} at {job_opening.company}"
            )
        )

        # Check if user has a job seeker profile
        try:
            profile = user.job_seeker_profile
        except JobSeekerProfile.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Job seeker {user.name} does not have a profile")
            )
            return

        # Check if job seeker has a talent sheet
        try:
            talent_sheet = profile.talent_sheet
            self.stdout.write(
                f"Found talent sheet (Published: {'Yes' if talent_sheet.is_published else 'No'})"
            )

            if not talent_sheet.is_published:
                self.stdout.write(
                    self.style.WARNING(
                        "Talent sheet is not published - this is required for matching"
                    )
                )
                return

        except TalentSheet.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f"Job seeker {user.name} does not have a talent sheet, which is required for matching"
                )
            )
            return

        # Display job opening information
        self.stdout.write("\n=== Job Opening Requirements ===")
        self.stdout.write(f"Title: {job_opening.title}")
        self.stdout.write(f"Company: {job_opening.company}")
        self.stdout.write(f"Location: {job_opening.location}")
        self.stdout.write(
            f"Required Experience: {job_opening.experience_required} years"
        )

        # Debug: Print raw required skills
        self.stdout.write(f"\nRaw Required Skills: {job_opening.required_skills}")

        # Debug: Print raw job seeker skills
        self.stdout.write(f"\nRaw Job Seeker Skills: {profile.skills}")

        if job_opening.required_skills:
            self.stdout.write("\nRequired Skills:")
            for skill in job_opening.required_skills_list:
                # Check if this skill appears in any of the job seeker's skills
                skill_matched = False
                if profile.skills:
                    # Extract keywords from job skill
                    job_skill_lower = skill.lower()
                    job_keywords = set()

                    # Add common technical keywords that may appear in both descriptions
                    technical_keywords = [
                        "sony",
                        "arri",
                        "canon",
                        "stabiliz",
                        "steadicam",
                        "ronin",
                        "movi",
                        "dji",
                        "inspire",
                        "drone",
                        "aerial",
                        "jib",
                        "crane",
                        "specialty",
                        "broadcast",
                        "camera",
                        "equipment",
                        "collaboration",
                        "communication",
                        "supervising",
                        "training",
                        "mentorship",
                        "team",
                    ]

                    for keyword in technical_keywords:
                        if keyword in job_skill_lower:
                            job_keywords.add(keyword)

                    # If no technical keywords found, just use the first few words
                    if not job_keywords and len(job_skill_lower.split()) > 2:
                        job_keywords = set(job_skill_lower.split()[:3])

                    # Check each of the job seeker's skills
                    for seeker_skill in profile.skills_list:
                        seeker_skill_lower = seeker_skill.lower()

                        # Check for keyword matches
                        for keyword in job_keywords:
                            if keyword in seeker_skill_lower:
                                skill_matched = True
                                break

                        if skill_matched:
                            break

                self.stdout.write(f"  - {skill} {'✓' if skill_matched else '✗'}")

        # Look for matches
        matches = CandidateMatch.objects.filter(
            job_opening=job_opening, talent_sheet=talent_sheet
        ).order_by("-holistic_score")

        if matches.exists():
            self.stdout.write("\n=== Match Information ===")
            self.stdout.write(
                f"Found {matches.count()} matches between this job seeker and job opening"
            )

            for i, match in enumerate(matches):
                self.stdout.write(f"\nMatch {i+1}:")
                self.stdout.write(f"Type: {match.match_type}")
                self.stdout.write(f"Score: {match.holistic_score}")
                self.stdout.write(f"Status: {match.status}")
                self.stdout.write(
                    f"Is Analyzed: {'Yes' if match.is_analyzed else 'No'}"
                )

                if match.match_summary:
                    self.stdout.write(f"Summary: {match.match_summary}")

                if match.match_analysis:
                    self.stdout.write("\nAnalysis:")
                    self.stdout.write(f"  {match.match_analysis}")
        else:
            self.stdout.write(
                self.style.WARNING(
                    "\nNo match found between this job seeker and job opening"
                )
            )

            # Analyze potential issues
            issues = []

            # Check experience years
            if (
                profile.years_of_experience
                and job_opening.experience_required
                and profile.years_of_experience < job_opening.experience_required
            ):
                issues.append(
                    f"Experience mismatch: Job requires {job_opening.experience_required} years, job seeker has {profile.years_of_experience} years"
                )

            # Check skills match
            if job_opening.required_skills and profile.skills:
                # Get all job skills as a list
                job_skills = job_opening.required_skills_list
                seeker_skills = profile.skills_list

                # Count matching skills using keyword matching
                matching_skills = []
                missing_skills = []

                # Technical keywords to check for in both skill sets
                technical_keywords = [
                    "sony",
                    "arri",
                    "canon",
                    "stabiliz",
                    "steadicam",
                    "ronin",
                    "movi",
                    "dji",
                    "inspire",
                    "drone",
                    "aerial",
                    "jib",
                    "crane",
                    "specialty",
                    "broadcast",
                    "camera",
                    "equipment",
                    "collaboration",
                    "communication",
                    "supervising",
                    "training",
                    "mentorship",
                    "team",
                ]

                for job_skill in job_skills:
                    skill_found = False
                    job_skill_lower = job_skill.lower()

                    # Extract keywords from job skill
                    job_keywords = set()
                    for keyword in technical_keywords:
                        if keyword in job_skill_lower:
                            job_keywords.add(keyword)

                    # If no technical keywords found, just use the first few words
                    if not job_keywords and len(job_skill_lower.split()) > 2:
                        job_keywords = set(job_skill_lower.split()[:3])

                    # Check if any of the job seeker's skills match these keywords
                    for seeker_skill in seeker_skills:
                        seeker_skill_lower = seeker_skill.lower()
                        for keyword in job_keywords:
                            if keyword in seeker_skill_lower:
                                matching_skills.append(job_skill)
                                skill_found = True
                                break

                        if skill_found:
                            break

                    if not skill_found:
                        missing_skills.append(job_skill)

                # Check for issues with skills matching
                if matching_skills:
                    self.stdout.write(
                        f"\nMatching skills: {len(matching_skills)} of {len(job_skills)}"
                    )
                    for skill in matching_skills:
                        self.stdout.write(f"  ✓ {skill}")

                if missing_skills:
                    if matching_skills:
                        issues.append(
                            f"Partial skill match: Job seeker has {len(matching_skills)} of {len(job_skills)} required skills"
                        )
                    else:
                        issues.append(
                            "No matching skills found between job requirements and job seeker"
                        )

            # Check role alignment
            if (
                profile.desired_role
                and job_opening.title
                and profile.desired_role.lower() not in job_opening.title.lower()
            ):
                issues.append(
                    f"Role mismatch: Job seeker desires '{profile.desired_role}', job is for '{job_opening.title}'"
                )

            # Check if talent sheet has ideal roles that might match
            if talent_sheet.ideal_roles:
                ideal_roles = [role.lower() for role in talent_sheet.ideal_roles_list]
                if not any(role in job_opening.title.lower() for role in ideal_roles):
                    issues.append(
                        "Job title doesn't match any of the job seeker's ideal roles"
                    )

            if issues:
                self.stdout.write("\nPotential reasons for no match:")
                for issue in issues:
                    self.stdout.write(f"  - {issue}")
            else:
                self.stdout.write(
                    "\nNo obvious issues found - the matching algorithm may need to be rerun"
                )
