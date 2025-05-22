import os
import time
import traceback
import uuid
from pathlib import Path

# Celery replacement for synchronous result polling
from celery.result import AsyncResult
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.authentication.models import User
from apps.core.tasks import safe_async_task
from apps.job_seekers.models import JobSeekerProfile
from apps.resume_processing.utils.pipeline import process_resume

# Define a timeout for waiting for the task (e.g., 5 minutes)
TASK_WAIT_TIMEOUT = 300  # seconds
TASK_POLL_INTERVAL = 2  # seconds


class Command(BaseCommand):
    help = "Batch ingest resume PDFs into the Hiredar system for testing purposes"

    def add_arguments(self, parser):
        # Required directory argument
        parser.add_argument(
            "directory",
            type=str,
            help="Directory containing resume files (PDF)",
        )

        # Option to join talent pool
        parser.add_argument(
            "--join_talent_pool",
            action="store_true",
            help="Automatically add job seekers to the talent pool and generate talent sheets",
        )

        # Option to limit number of resumes processed
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of resumes to process",
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
        join_talent_pool = options["join_talent_pool"]
        limit = options["limit"]

        try:
            self.ingest_resumes(directory_path, verbosity, join_talent_pool, limit)
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING("\nScript interrupted by user. Exiting...")
            )
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Unhandled error: {e}"))
            traceback.print_exc()
            return

    def ingest_resumes(
        self,
        directory_path: str,
        verbosity: int,
        join_talent_pool: bool = False,
        limit: int | None = None,
    ) -> None:
        """
        Process all resumes in the given directory.

        Args:
            directory_path: Path to directory containing resume files
            verbosity: Output verbosity level (0-3)
            join_talent_pool: Whether to add job seekers to the talent pool
            limit: Optional limit on number of resumes to process
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

        # Apply limit if specified
        if limit and limit > 0:
            resume_files = resume_files[:limit]
            self.stdout.write(self.style.SUCCESS(f"Limiting to {limit} resume files"))

        self.stdout.write(
            self.style.SUCCESS(f"Found {len(resume_files)} resume files to process")
        )

        # Process each resume
        success_count = 0
        failure_count = 0
        talent_sheet_count = 0

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

                    # Print the updated profile details
                    self.stdout.write(
                        f"Profile updated successfully for {user.email}:\n"
                        f"  - Name: {user.name}\n"
                        f"  - Most recent title: {profile.most_recent_title}"
                    )

                # If requested, add the job seeker to the talent pool
                if join_talent_pool:
                    talent_sheet_created = self.add_to_talent_pool(profile, verbosity)
                    if talent_sheet_created:
                        talent_sheet_count += 1
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

        if join_talent_pool:
            self.stdout.write(
                self.style.SUCCESS(f"TALENT SHEETS CREATED: {talent_sheet_count}")
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
                name=f"Test{counter} User{counter}",
                user_type="job_seeker",
            )

            # A JobSeekerProfile should be created automatically via signals
            profile = JobSeekerProfile.objects.get(user_owner=user)

            return user, profile
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating test user: {e}"))
            traceback.print_exc()
            return None, None

    def add_to_talent_pool(self, profile: JobSeekerProfile, verbosity: int) -> bool:
        """
        Add a job seeker to the talent pool by scheduling the task
        and waiting for its completion.

        Args:
            profile: The JobSeekerProfile to add to the talent pool
            verbosity: Output verbosity level (0-3)

        Returns:
            True if talent sheet was created successfully, False otherwise
        """
        task_id = None
        try:
            if verbosity >= 1:
                email = (
                    profile.user_owner.email
                    if profile.user_owner
                    else "unknown@example.com"
                )
                self.stdout.write(f"  - Scheduling talent sheet generation for {email}")

            # Schedule the talent sheet generation task to run asynchronously
            profile_id = getattr(profile, "id")
            task_id = safe_async_task(
                "apps.job_seekers.tasks.talent_sheet_tasks.generate_talent_sheet_task",
                profile_id,
                task_name=f"generate_talent_sheet_{profile_id}",
                timeout=300,
            )

            if verbosity >= 1:
                self.stdout.write(
                    f"  - Task {task_id} scheduled. Waiting for completion..."
                )

            # Wait for the task to complete
            start_time = time.time()
            result_obj: AsyncResult | None = None
            while time.time() - start_time < TASK_WAIT_TIMEOUT:
                result_obj = AsyncResult(task_id)
                if result_obj.state in {"SUCCESS", "FAILURE"}:
                    if verbosity >= 1:
                        self.stdout.write(
                            f"  - Task {task_id} completed with state {result_obj.state}."
                        )
                    break

                if verbosity >= 2:
                    self.stdout.write(
                        f"  - Task {task_id} state {result_obj.state}, waiting..."
                    )

                time.sleep(TASK_POLL_INTERVAL)
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"  - Timeout: Task {task_id} did not complete within {TASK_WAIT_TIMEOUT}s"
                    )
                )
                return False

            # Evaluate task outcome
            if result_obj and result_obj.successful():
                if verbosity >= 1:
                    email = (
                        profile.user_owner.email
                        if profile.user_owner
                        else "unknown@example.com"
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f"  - Created talent sheet for {email}")
                    )
                return True
            else:
                # Task failed or wasn't fetched correctly
                error_message = "Unknown error"
                if task:
                    # Try to get the error message from the task result if it failed
                    if isinstance(task.result, dict):
                        error_message = task.result.get(
                            "message", "Task failed without specific message"
                        )
                    elif (
                        task.result
                    ):  # If result is not None/dict, use its string representation
                        error_message = str(task.result)
                    else:
                        error_message = "Task failed without returning a result."
                else:
                    error_message = "Task could not be fetched after scheduling."

                self.stdout.write(
                    self.style.ERROR(
                        f"  - Failed to create talent sheet: {error_message}"
                    )
                )
                return False

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  - Error during talent pool processing: {str(e)}")
            )
            # If an exception occurs *before* or *during* polling, log it
            if verbosity >= 2:
                traceback.print_exc()
            return False

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
            # Make sure the directory exists in MEDIA_ROOT
            media_temp_dir = os.path.join(settings.MEDIA_ROOT, temp_dir)
            os.makedirs(media_temp_dir, exist_ok=True)

            # Create a unique filename
            temp_filename = f"temp_{uuid.uuid4().hex}.pdf"
            temp_rel_path = f"{temp_dir}/{temp_filename}"
            temp_abs_path = os.path.join(settings.MEDIA_ROOT, temp_rel_path)

            # Save the file directly to the filesystem
            with open(temp_abs_path, "wb") as f:
                f.write(file_content)

            # Keep track of the path for cleanup
            saved_path = temp_abs_path

            self.stdout.write(f"Processing resume: {os.path.basename(resume_path)}")

            if verbosity >= 2:
                self.stdout.write(f"  - Using temporary file: {temp_abs_path}")
                self.stdout.write("  - Processing resume through pipeline...")

            # Use the unified pipeline to process the resume with the absolute path
            result = process_resume(temp_abs_path, profile)

            if not result["success"]:
                # Display detailed error information
                error_msg = result.get("message", "Unknown error")

                # Show which step failed
                pipeline_steps = result.get("pipeline_steps", {})
                failed_at = "unknown step"

                # Handle both dict and list formats for backward compatibility
                if isinstance(pipeline_steps, dict):
                    for step, completed in pipeline_steps.items():
                        if not completed:
                            failed_at = step.replace("_", " ")
                            break
                elif isinstance(pipeline_steps, list) and len(pipeline_steps) > 0:
                    # If it's a list, assume the last item is where it failed
                    # This is a best guess since we don't have completion flags
                    failed_at = pipeline_steps[-1].replace("_", " ")

                self.stdout.write(
                    self.style.ERROR(f"  - ERROR in {failed_at}: {error_msg}")
                )

                # Show detailed exception information at higher verbosity
                if verbosity >= 2 and "exception" in result:
                    self.stdout.write(
                        self.style.ERROR(f"  - Exception: {result['exception']}")
                    )

                # Always clean up temporary file if it exists
                if saved_path and os.path.exists(saved_path):
                    try:
                        os.remove(saved_path)
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
                # Handle both dict and list formats for backward compatibility
                if isinstance(pipeline_steps, dict):
                    for step, completed in pipeline_steps.items():
                        step_name = step.replace("_", " ")
                        self.stdout.write(
                            f"  - {step_name}: {'✓' if completed else '✗'}"
                        )
                elif isinstance(pipeline_steps, list):
                    for step in pipeline_steps:
                        step_name = step.replace("_", " ")
                        self.stdout.write(f"  - {step_name}: ✓")

                # Show processing time if available
                if result.get("processing_time"):
                    self.stdout.write(
                        f"  - Processing time: {result['processing_time']:.2f}s"
                    )

            # Clean up temporary file if it exists
            if saved_path and os.path.exists(saved_path):
                try:
                    os.remove(saved_path)
                except Exception:
                    pass

            return True

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  - CRITICAL ERROR: {str(e)}"))
            if verbosity >= 2:
                self.stdout.write(self.style.ERROR("  - Traceback:"))
                for line in traceback.format_exc().splitlines():
                    self.stdout.write(self.style.ERROR(f"    {line}"))

            # Always clean up temporary file if it exists
            if saved_path and os.path.exists(saved_path):
                try:
                    os.remove(saved_path)
                except Exception:
                    pass

            return False
