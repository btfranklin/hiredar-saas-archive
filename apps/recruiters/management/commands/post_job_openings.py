"""
Management command to post job openings from sample data.

This command creates a test recruiter account and posts job openings
by processing markdown files from the sample_data directory.
"""

import os
import re
import traceback
import uuid
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.authentication.models import User
from apps.recruiters.models import JobOpening, RecruiterProfile


class Command(BaseCommand):
    """Post job openings from sample data files."""

    help = (
        "Create test recruiter account and post job openings from sample markdown files"
    )

    def add_arguments(self, parser):
        """Add command arguments."""
        # Optional directory argument
        parser.add_argument(
            "--directory",
            type=str,
            default="sample_data/job_openings",
            help="Directory containing job opening markdown files",
        )

        # Optional flag to activate all job openings
        parser.add_argument(
            "--activate",
            action="store_true",
            help="Automatically activate all job openings (status='active')",
        )

        # Optional limit argument
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of job openings to process",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        directory_path = options["directory"]
        verbosity = options["verbosity"]  # Django's built-in verbosity level (0-3)
        activate = options["activate"]
        limit = options["limit"]

        try:
            self.post_job_openings(directory_path, verbosity, activate, limit)
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING("\nScript interrupted by user. Exiting...")
            )
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Unhandled error: {e}"))
            traceback.print_exc()
            return

    def post_job_openings(
        self,
        directory_path: str,
        verbosity: int,
        activate: bool = False,
        limit: int | None = None,
    ) -> None:
        """
        Process all job opening files in the given directory.

        Args:
            directory_path: Path to directory containing job opening files
            verbosity: Output verbosity level (0-3)
            activate: Whether to activate all job openings
            limit: Optional limit on number of job openings to process
        """
        job_dir = Path(directory_path)

        if not job_dir.exists() or not job_dir.is_dir():
            self.stdout.write(
                self.style.ERROR(f"Error: {directory_path} is not a valid directory")
            )
            return

        # Get all markdown files in the directory
        job_files = list(job_dir.glob("*.md"))

        if not job_files:
            self.stdout.write(
                self.style.WARNING(f"No markdown files found in {directory_path}")
            )
            return

        # Apply limit if specified
        if limit and limit > 0:
            job_files = job_files[:limit]

        self.stdout.write(
            self.style.SUCCESS(f"Found {len(job_files)} job opening files to process")
        )

        # Create a test recruiter for these job openings
        recruiter_profile = self.create_test_recruiter()
        if not recruiter_profile:
            self.stdout.write(
                self.style.ERROR("Failed to create test recruiter. Exiting.")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Created test recruiter: {recruiter_profile.user.email}"
            )
        )

        # Process each job file
        success_count = 0
        failure_count = 0

        for i, job_file in enumerate(job_files, 1):
            # Always show which file we're processing
            self.stdout.write(
                self.style.NOTICE(
                    f"\n[{i}/{len(job_files)}] Processing: {job_file.name}"
                )
            )

            # Process the job file
            success = self.process_job_file(
                str(job_file), recruiter_profile, activate, verbosity
            )

            if success:
                success_count += 1
                if verbosity >= 1:
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ Successfully processed {job_file.name}")
                    )
            else:
                failure_count += 1
                self.stdout.write(
                    self.style.ERROR(f"❌ Failed to process {job_file.name}")
                )

        # Print summary at the end - always show this regardless of verbosity
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(f"SUMMARY: Processed {len(job_files)} job opening files")
        self.stdout.write(self.style.SUCCESS(f"SUCCESS: {success_count} job openings"))
        self.stdout.write(
            self.style.ERROR(f"FAILURE: {failure_count} job openings")
            if failure_count
            else "FAILURE: 0 job openings"
        )

        if success_count > 0 and not activate:
            self.stdout.write(
                self.style.WARNING(
                    "\nNOTE: Job openings are created with 'draft' status by default."
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "To activate them (which will trigger embedding creation), use:"
                )
            )
            self.stdout.write("  python manage.py post_job_openings --activate")

        self.stdout.write("=" * 50)

    def create_test_recruiter(self) -> RecruiterProfile | None:
        """
        Create a test recruiter account for posting job openings.

        Returns:
            A RecruiterProfile instance or None if creation fails
        """
        unique_id = uuid.uuid4().hex[:8]
        email = f"test_recruiter_{unique_id}@example.com"

        try:
            # Use the UserManager's create_user method
            user = User.objects.create_user(  # type: ignore
                email=email,
                password="testpassword123",
                name=f"Test Recruiter {unique_id}",
                user_type="recruiter",
            )

            # A RecruiterProfile should be created automatically via signals
            profile = RecruiterProfile.objects.get(user=user)

            return profile
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating test recruiter: {e}"))
            traceback.print_exc()
            return None

    def process_job_file(
        self,
        file_path: str,
        recruiter_profile: RecruiterProfile,
        activate: bool,
        verbosity: int,
    ) -> bool:
        """
        Process a job opening markdown file and create a JobOpening.

        Args:
            file_path: Path to the job markdown file
            recruiter_profile: RecruiterProfile to associate with the job
            activate: Whether to set status to 'active'
            verbosity: Output verbosity level (0-3)

        Returns:
            True if processing was successful, False otherwise
        """
        try:
            # Read the markdown file
            with open(file_path, "r") as f:
                content = f.read()

            # Extract job data from the content instead of filename
            job_data = self.parse_job_markdown(content)
            if not job_data:
                self.stdout.write(
                    self.style.ERROR(f"Failed to extract job data from {file_path}")
                )
                return False

            # Create the JobOpening
            job = JobOpening(
                recruiter=recruiter_profile,
                title=job_data.get("title", "Untitled Job"),
                company=job_data.get("company", "Unknown Company"),
                description=job_data.get("description", ""),
                location=job_data.get("location", ""),
                job_level=job_data.get("job_level", ""),
                employment_type=job_data.get("employment_type", "full_time"),
                required_skills=job_data.get("required_skills", ""),
                required_qualifications=job_data.get("required_qualifications", ""),
                responsibilities=job_data.get("responsibilities", ""),
                daily_tasks=job_data.get("daily_tasks", ""),
                salary_min=job_data.get("salary_min"),
                salary_max=job_data.get("salary_max"),
                benefits=job_data.get("benefits", ""),
                soft_skills=job_data.get("soft_skills", ""),
                experience_required=job_data.get("experience_required", ""),
                work_environment=job_data.get("work_environment", ""),
                working_hours=job_data.get("working_hours", ""),
                status="active" if activate else "draft",
            )

            job.save()

            if verbosity >= 1:
                self.stdout.write(
                    f"Created job opening: {job.pk} - {job.title} at {job.company}"
                )
                self.stdout.write(f"  - Status: {job.status}")

            return True

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error processing job file {file_path}: {e}")
            )
            if verbosity >= 2:
                traceback.print_exc()
            return False

    def parse_job_markdown(self, content: str) -> dict:
        """
        Parse a job opening markdown file to extract structured data.

        Args:
            content: Markdown content of the job file

        Returns:
            Dictionary with extracted job data
        """
        job_data = {}

        # Extract job title (H1 heading)
        title_match = re.search(r"^#\s+(.*?)$", content, re.MULTILINE)
        if title_match:
            job_data["title"] = title_match.group(1).strip()

        # Extract company name
        company_match = re.search(
            r"\*\*Company:\*\*\s+(.*?)(?:\s+\n|\s+\|)", content, re.MULTILINE
        )
        if company_match:
            job_data["company"] = company_match.group(1).strip()

        # Extract location
        location_match = re.search(
            r"\*\*Location:\*\*\s+(.*?)(?:\s+\n|\s+\|)", content, re.MULTILINE
        )
        if location_match:
            job_data["location"] = location_match.group(1).strip()

        # Extract salary range
        salary_match = re.search(
            r"\*\*Salary Range:\*\*\s+\$(\d+),?(\d+)?\s*-\s*\$(\d+),?(\d+)?", content
        )
        if salary_match:
            # Handle comma-separated numbers
            min_salary_parts = [p for p in salary_match.groups()[0:2] if p]
            max_salary_parts = [p for p in salary_match.groups()[2:4] if p]

            try:
                min_salary = int("".join(min_salary_parts))
                max_salary = int("".join(max_salary_parts))
                job_data["salary_min"] = min_salary
                job_data["salary_max"] = max_salary
            except (ValueError, TypeError):
                # If parsing fails, just skip the salary
                pass

        # Extract employment type
        employment_match = re.search(
            r"\*\*Employment Type:\*\*\s+(.*?)(?:\s+\n|\s+\|)", content, re.MULTILINE
        )
        if employment_match:
            employment_text = employment_match.group(1).lower()
            if "full" in employment_text and "time" in employment_text:
                job_data["employment_type"] = "full_time"
            elif "part" in employment_text and "time" in employment_text:
                job_data["employment_type"] = "part_time"
            elif "contract" in employment_text:
                job_data["employment_type"] = "contract"
            elif "temp" in employment_text:
                job_data["employment_type"] = "temporary"
            elif "intern" in employment_text:
                job_data["employment_type"] = "internship"

        # Extract job level
        if "job_level" not in job_data and employment_match:
            employment_text = employment_match.group(1).lower()
            for level in ["entry", "junior", "mid", "senior", "manager", "executive"]:
                if level in employment_text:
                    job_data["job_level"] = level
                    break

        # Extract description - combine overview and about company
        description = []

        # About company section
        about_match = re.search(r"## About .*?\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
        if about_match:
            description.append(about_match.group(1).strip())

        # Job overview section
        overview_match = re.search(
            r"## Job Overview\n(.*?)(?=\n##|\Z)", content, re.DOTALL
        )
        if overview_match:
            description.append(overview_match.group(1).strip())

        if description:
            job_data["description"] = "\n\n".join(description)

        # Extract sections
        sections = re.findall(r"## (.*?)\n(.*?)(?=\n## |\Z)", content, re.DOTALL)

        for section_title, section_content in sections:
            section_title = section_title.strip().lower()
            section_content = section_content.strip()

            # Map section titles to model fields
            if "qualifications" in section_title and "required" in section_title:
                job_data["required_qualifications"] = section_content
            elif "qualifications" in section_title and "preferred" in section_title:
                # Add to required skills if it's a preferred qualification
                if "required_skills" in job_data:
                    job_data["required_skills"] += " | " + section_content
                else:
                    job_data["required_skills"] = section_content
            elif "skills" in section_title and "soft" not in section_title:
                if "required_skills" in job_data:
                    job_data["required_skills"] += " | " + section_content
                else:
                    job_data["required_skills"] = section_content
            elif "soft skills" in section_title:
                job_data["soft_skills"] = section_content
            elif (
                "responsibilities" in section_title
                or "key responsibilities" in section_title
            ):
                job_data["responsibilities"] = section_content
            elif "tasks" in section_title or "duties" in section_title:
                job_data["daily_tasks"] = section_content
            elif "experience" in section_title:
                job_data["experience_required"] = section_content
            elif "benefits" in section_title or "perks" in section_title:
                job_data["benefits"] = section_content
            elif "working" in section_title and "hour" in section_title:
                job_data["working_hours"] = section_content
            elif "environment" in section_title:
                job_data["work_environment"] = section_content

        return job_data
