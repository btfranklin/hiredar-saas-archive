"""Management command to batch ingest resume PDFs for local testing."""

import os
import time
import traceback
import uuid
from pathlib import Path
from typing import Any

from celery.result import AsyncResult
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.authentication.models import User
from apps.candidates.models import CandidatePool, CandidateProfile
from apps.candidates.tasks.profile_enrichment_tasks import (
    generate_profile_enrichment_task,
)
from apps.core.tasks import safe_async_task
from apps.candidates.services.resume_pipeline import process_resume as run_resume_pipeline

# Define a timeout for waiting for the task (e.g., 5 minutes)
TASK_WAIT_TIMEOUT = 300  # seconds
TASK_POLL_INTERVAL = 2  # seconds
TEMP_RESUME_DIR = "resumes"


class Command(BaseCommand):
    """Command to ingest batches of resumes for development workflows."""
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
            help="Automatically queue candidate profile enrichment tasks",
        )

        # Option to limit number of resumes processed
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of resumes to process",
        )

    def _profile_label(self, profile: CandidateProfile) -> str:
        """Return a descriptive label for logging about the candidate profile."""
        candidate_name = getattr(profile, "candidate_name", "") or ""
        if candidate_name:
            return candidate_name

        recent_title = getattr(profile, "most_recent_title", "") or ""
        if recent_title:
            return recent_title

        try:
            pool = profile.pool  # type: ignore[attr-defined]
            recruiter = getattr(pool, "recruiter", None)
            if recruiter and getattr(recruiter, "email", None):
                return recruiter.email  # type: ignore[return-value]
        except Exception:  # pragma: no cover - defensive
            pass

        return f"candidate-{getattr(profile, 'pk', 'unknown')}"

    def _persist_temp_resume(self, file_content: bytes) -> Path:
        """Write resume bytes to disk for downstream processing."""
        media_temp_dir = Path(settings.MEDIA_ROOT) / TEMP_RESUME_DIR
        media_temp_dir.mkdir(parents=True, exist_ok=True)

        temp_path = media_temp_dir / f"temp_{uuid.uuid4().hex}.pdf"
        temp_path.write_bytes(file_content)
        return temp_path

    def _cleanup_temp_file(self, saved_path: Path | None) -> None:
        """Remove temporary resume file if it exists."""
        if saved_path is None:
            return

        try:
            if saved_path.exists():
                saved_path.unlink()
        except OSError:
            # Best-effort cleanup is enough for a development command.
            pass

    def _infer_failed_step(self, pipeline_steps: Any) -> str:
        """Infer the pipeline stage that failed from mixed return formats."""
        if isinstance(pipeline_steps, dict):
            for step, completed in pipeline_steps.items():
                if not completed:
                    return step.replace("_", " ")
        if isinstance(pipeline_steps, list) and pipeline_steps:
            return pipeline_steps[-1].replace("_", " ")
        return "unknown step"

    def _log_pipeline_failure(self, result: dict[str, Any], verbosity: int) -> None:
        """Log diagnostics for failed resume processing."""
        error_msg = result.get("message", "Unknown error")
        failed_at = self._infer_failed_step(result.get("pipeline_steps"))
        self.stdout.write(self.style.ERROR(f"  - ERROR in {failed_at}: {error_msg}"))

        if verbosity >= 2 and "exception" in result:
            self.stdout.write(self.style.ERROR(f"  - Exception: {result['exception']}"))

    def _log_pipeline_success(self, result: dict[str, Any], verbosity: int) -> None:
        """Emit verbose details for completed resume processing."""
        if verbosity < 2:
            return

        pipeline_steps = result.get("pipeline_steps", {})
        if isinstance(pipeline_steps, dict):
            for step, completed in pipeline_steps.items():
                step_label = step.replace("_", " ")
                status = "✓" if completed else "✗"
                self.stdout.write(f"  - {step_label}: {status}")
        elif isinstance(pipeline_steps, list):
            for step in pipeline_steps:
                step_label = step.replace("_", " ")
                self.stdout.write(f"  - {step_label}: ✓")

        processing_time = result.get("processing_time")
        if processing_time:
            self.stdout.write(f"  - Processing time: {processing_time:.2f}s")

    def _extract_task_error(self, result_obj: AsyncResult | None) -> str:
        """Best-effort extraction of an error message from an async task."""
        if result_obj is None:
            return "Task could not be fetched after scheduling."

        try:
            task_result = result_obj.result
        except Exception:  # pylint: disable=broad-except
            info = getattr(result_obj, "info", None)
            return str(info) if info else "Task failed without returning a result."

        if isinstance(task_result, dict):
            return task_result.get("message", "Task failed without specific message")

        if task_result:
            return str(task_result)

        return "Task failed without returning a result."

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
            join_talent_pool: Whether to queue candidate enrichment tasks
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
        enrichment_count = 0

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
            if self.process_resume(str(resume_file), profile, verbosity):
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

                # If requested, queue enrichment tasks for the candidate
                if join_talent_pool and self.add_to_talent_pool(profile, verbosity):
                    enrichment_count += 1
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
                self.style.SUCCESS(
                    f"PROFILE ENRICHMENTS QUEUED: {enrichment_count}"
                )
            )

        self.stdout.write("=" * 50)

    def create_test_user(
        self, counter: int
    ) -> tuple[User, CandidateProfile] | tuple[None, None]:
        """
        Create a test recruiter and candidate profile for testing purposes.

        Args:
            counter: A counter to ensure unique usernames/emails

        Returns:
            A tuple containing the created recruiter user and candidate profile, or (None, None) if creation fails
        """
        unique_id = f"{counter}_{uuid.uuid4().hex[:8]}"
        email = f"test_recruiter_{unique_id}@example.com"

        try:
            # Use the UserManager's create_user method
            user = User.objects.create_user(  # type: ignore
                email=email,
                password="testpassword123",
                name=f"Test Recruiter {counter}",
                user_type="recruiter",
            )

            pool = CandidatePool.objects.create(
                recruiter=user,
                name=f"Dev Upload Pool {unique_id}",
            )
            profile = CandidateProfile.objects.create(pool=pool)

            return user, profile
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating test user: {e}"))
            traceback.print_exc()
            return None, None

    def add_to_talent_pool(self, profile: CandidateProfile, verbosity: int) -> bool:
        """
        Trigger profile enrichment for the candidate by scheduling the task
        and waiting for its completion.

        Args:
            profile: The CandidateProfile to enrich
            verbosity: Output verbosity level (0-3)

        Returns:
            True if enrichment completed successfully, False otherwise
        """
        task_id: str | None = None
        try:
            profile_label = self._profile_label(profile)
            if verbosity >= 1:
                self.stdout.write(
                    f"  - Scheduling profile enrichment for {profile_label}"
                )

            # Schedule the talent sheet generation task to run asynchronously
            profile_id = getattr(profile, "id")
            task_id = safe_async_task(
                generate_profile_enrichment_task,
                profile_id,
                task_name=f"generate_profile_enrichment_{profile_id}",
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

            if result_obj is None or result_obj.state not in {"SUCCESS", "FAILURE"}:
                self.stdout.write(
                    self.style.ERROR(
                        f"  - Timeout: Task {task_id} did not complete within {TASK_WAIT_TIMEOUT}s"
                    )
                )
                return False

            if result_obj.successful():
                if verbosity >= 1:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  - Generated profile enrichment for {profile_label}"
                        )
                    )
                return True

            error_message = self._extract_task_error(result_obj)
            self.stdout.write(
                self.style.ERROR(
                    f"  - Failed to generate profile enrichment: {error_message}"
                )
            )
            return False

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"  - Error during profile enrichment: {str(e)}"
                )
            )
            # If an exception occurs *before* or *during* polling, log it
            if verbosity >= 2:
                traceback.print_exc()
            return False

    def process_resume(
        self, resume_path: str, profile: CandidateProfile, verbosity: int
    ) -> bool:
        """
        Process a resume file and update the given profile with extracted information.

        Args:
            resume_path: Path to the resume file
            profile: CandidateProfile to update
            verbosity: Output verbosity level (0-3)

        Returns:
            True if processing was successful, False otherwise
        """
        saved_path: Path | None = None
        try:
            try:
                file_content = Path(resume_path).read_bytes()
            except OSError as exc:
                self.stdout.write(self.style.ERROR(f"  - ERROR reading file: {exc}"))
                return False

            try:
                saved_path = self._persist_temp_resume(file_content)
            except OSError as exc:
                self.stdout.write(
                    self.style.ERROR(f"  - ERROR creating temp resume: {exc}")
                )
                return False

            self.stdout.write(f"Processing resume: {Path(resume_path).name}")

            if verbosity >= 2:
                self.stdout.write(f"  - Using temporary file: {saved_path}")
                self.stdout.write("  - Processing resume through pipeline...")

            # Use the unified pipeline to process the resume with the absolute path
            result = run_resume_pipeline(str(saved_path), profile)

            if not result.get("success"):
                self._log_pipeline_failure(result, verbosity)
                return False

            if verbosity >= 1:
                self.stdout.write(
                    self.style.SUCCESS("  - SUCCESS: Profile updated successfully")
                )

            self._log_pipeline_success(result, verbosity)
            return True

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  - CRITICAL ERROR: {str(e)}"))
            if verbosity >= 2:
                self.stdout.write(self.style.ERROR("  - Traceback:"))
                for line in traceback.format_exc().splitlines():
                    self.stdout.write(self.style.ERROR(f"    {line}"))
            return False
        finally:
            self._cleanup_temp_file(saved_path)
