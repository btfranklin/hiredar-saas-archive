import os
import traceback
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from apps.authentication.models import User
from apps.job_seekers.models import JobSeekerProfile
from apps.job_seekers.utils.resume_processing.pipeline import process_resume


class Command(BaseCommand):
    help = "Batch ingest resume PDFs into the Hiredar system for testing purposes"

    def add_arguments(self, parser):
        # Required directory argument
        parser.add_argument(
            "directory",
            type=str,
            help="Directory containing resume files (PDF)",
        )

    def handle(self, *args, **options):
        # Check if the OpenAI API key is set
        if "OPENAI_API_KEY" not in os.environ and not hasattr(
            settings, "OPENAI_API_KEY"
        ):
            self.stdout.write(
                self.style.WARNING(
                    "WARNING: OPENAI_API_KEY environment variable is not set."
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "The resume processing may fail when calling the OpenAI API."
                )
            )

        directory_path = options["directory"]
        verbosity = options["verbosity"]  # Django's built-in verbosity level (0-3)

        try:
            self.ingest_resumes(directory_path, verbosity)
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING("\nScript interrupted by user. Exiting...")
            )
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Unhandled error: {e}"))
            traceback.print_exc()
            return

    def ingest_resumes(self, directory_path: str, verbosity: int) -> None:
        """
        Process all resumes in the given directory.

        Args:
            directory_path: Path to directory containing resume files
            verbosity: Output verbosity level (0-3)
        """
        resume_dir = Path(directory_path)

        if not resume_dir.exists() or not resume_dir.is_dir():
            self.stdout.write(
                self.style.ERROR(f"Error: {directory_path} is not a valid directory")
            )
            return

        # Get all PDF files in the directory
        resume_files = list(resume_dir.glob("*.pdf"))

        if not resume_files:
            self.stdout.write(
                self.style.WARNING(f"No PDF files found in {directory_path}")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f"Found {len(resume_files)} resume files to process")
        )

        # Process each resume
        success_count = 0
        failure_count = 0

        for i, resume_file in enumerate(resume_files, 1):
            # Always show which file we're processing
            self.stdout.write(
                self.style.NOTICE(
                    f"\n[{i}/{len(resume_files)}] Processing: {resume_file.name}"
                )
            )

            # Create a test user for this resume
            user, profile = self.create_test_user(i)

            if not user or not profile:
                self.stdout.write(
                    self.style.ERROR(
                        f"  - Failed to create user for resume {resume_file.name}"
                    )
                )
                failure_count += 1
                continue

            # Process the resume and update the profile
            success = self.process_resume(str(resume_file), profile, verbosity)

            if success:
                success_count += 1
                if verbosity >= 1:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Successfully processed resume for {user.email}"
                        )
                    )

                    # Display profile information at higher verbosity
                    if verbosity >= 2:
                        self.stdout.write(
                            f"  - Current position: {profile.current_position}"
                        )
                        self.stdout.write(
                            f"  - Years of experience: {profile.years_of_experience}"
                        )
                        skills_display = (
                            ", ".join(profile.skills_list[:5])
                            if profile.skills_list
                            else "None"
                        )
                        if len(profile.skills_list) > 5:
                            skills_display += "..."
                        self.stdout.write(f"  - Skills: {skills_display}")
            else:
                failure_count += 1
                self.stdout.write(
                    self.style.ERROR(f"❌ Failed to process resume for {user.email}")
                )

        # Print summary at the end - always show this regardless of verbosity
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(f"SUMMARY: Processed {len(resume_files)} resumes")
        self.stdout.write(self.style.SUCCESS(f"SUCCESS: {success_count} resumes"))
        self.stdout.write(
            self.style.ERROR(f"FAILURE: {failure_count} resumes")
            if failure_count
            else "FAILURE: 0 resumes"
        )
        self.stdout.write("=" * 50)

    def create_test_user(
        self, counter: int
    ) -> tuple[User, JobSeekerProfile] | tuple[None, None]:
        """
        Create a test user and job seeker profile for testing purposes.

        Args:
            counter: A counter to ensure unique usernames/emails

        Returns:
            A tuple containing the created user and job seeker profile, or (None, None) if creation fails
        """
        unique_id = f"{counter}_{uuid.uuid4().hex[:8]}"
        email = f"test_user_{unique_id}@example.com"

        try:
            # Use the UserManager's create_user method
            user = User.objects.create_user(  # type: ignore
                email=email,
                password="testpassword123",
                first_name=f"Test{counter}",
                last_name=f"User{counter}",
                user_type="job_seeker",
            )

            # A JobSeekerProfile should be created automatically via signals
            profile = JobSeekerProfile.objects.get(user=user)

            return user, profile
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating test user: {e}"))
            traceback.print_exc()
            return None, None

    def process_resume(
        self, resume_path: str, profile: JobSeekerProfile, verbosity: int
    ) -> bool:
        """
        Process a resume file and update the given profile with extracted information.

        Args:
            resume_path: Path to the resume file
            profile: JobSeekerProfile to update
            verbosity: Output verbosity level (0-3)

        Returns:
            True if processing was successful, False otherwise
        """
        saved_path = None

        try:
            # Step 1: Read the PDF file
            try:
                with open(resume_path, "rb") as f:
                    file_content = f.read()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  - ERROR reading file: {str(e)}"))
                return False

            # Step 2: Save the resume temporarily
            temp_dir = "resumes"
            # Make sure the directory exists
            os.makedirs(os.path.join(settings.MEDIA_ROOT, temp_dir), exist_ok=True)

            temp_path = f"{temp_dir}/temp_{uuid.uuid4().hex}.pdf"
            saved_path = default_storage.save(temp_path, ContentFile(file_content))

            self.stdout.write(f"Processing resume: {os.path.basename(resume_path)}")

            # Use the unified pipeline to process the resume
            if verbosity >= 2:
                self.stdout.write("  - Processing resume through pipeline...")

            result = process_resume(saved_path, profile)

            if not result["success"]:
                # Display detailed error information
                error_msg = result.get("message", "Unknown error")

                # Show which step failed
                pipeline_steps = result.get("pipeline_steps", {})
                failed_at = "unknown step"
                for step, completed in pipeline_steps.items():
                    if not completed:
                        failed_at = step.replace("_", " ")
                        break

                self.stdout.write(
                    self.style.ERROR(f"  - ERROR in {failed_at}: {error_msg}")
                )

                # Show detailed exception information at higher verbosity
                if verbosity >= 2 and "exception" in result:
                    self.stdout.write(
                        self.style.ERROR(f"  - Exception: {result['exception']}")
                    )

                # Always clean up temporary file if it exists
                if saved_path:
                    try:
                        default_storage.delete(saved_path)
                    except Exception:
                        pass

                return False

            if verbosity >= 1:
                self.stdout.write(
                    self.style.SUCCESS("  - SUCCESS: Profile updated successfully")
                )

            # Show detailed processing information at higher verbosity levels
            if verbosity >= 2:
                # Show pipeline steps completion
                pipeline_steps = result.get("pipeline_steps", {})
                for step, completed in pipeline_steps.items():
                    step_name = step.replace("_", " ")
                    self.stdout.write(f"  - {step_name}: {'✓' if completed else '✗'}")

                # Show processing time if available
                if result.get("processing_time"):
                    self.stdout.write(
                        f"  - Processing time: {result['processing_time']:.2f}s"
                    )

            return True

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  - CRITICAL ERROR: {str(e)}"))
            if verbosity >= 2:
                self.stdout.write(self.style.ERROR("  - Traceback:"))
                for line in traceback.format_exc().splitlines():
                    self.stdout.write(self.style.ERROR(f"    {line}"))

            # Always clean up temporary file if it exists
            if saved_path:
                try:
                    default_storage.delete(saved_path)
                except Exception:
                    pass

            return False
