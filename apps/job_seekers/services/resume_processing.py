"""
Service for handling resume processing tasks.
"""

import os
import shutil
import tempfile
import uuid
from zipfile import ZipFile

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django_q.tasks import async_task, result

from apps.authentication.models import User
from apps.job_seekers.models.profile import UploadedResumePool
from apps.job_seekers.services.profile_manager import ProfileManager
from apps.recruiters.models import JobOpening
from apps.resume_processing.models import ResumeProcessingTaskProgress


class DummyTaskProgress:
    """A dummy task progress object for when we only have Django Q2 results."""

    def __init__(self, task_id, result_data):
        """Initialize with task ID and result data."""
        self.task_id = task_id
        self.status = (
            "completed" if result_data.get("status", "error") == "success" else "failed"
        )
        self.message = result_data.get("message", "")
        self._result_data = result_data

    def to_dict(self):
        """Convert to dictionary representation."""
        return {
            "progress_percent": (
                100 if self._result_data.get("status", "error") == "success" else 0
            ),
            "current_step": (
                "completed"
                if self._result_data.get("status", "error") == "success"
                else "failed"
            ),
            "current_step_name": (
                "Complete"
                if self._result_data.get("status", "error") == "success"
                else "Failed"
            ),
            "steps": [],
        }


class ResumeProcessor:
    """Service for handling resume processing tasks."""

    @staticmethod
    def create_processing_task(user, task_id):
        """
        Create a new resume processing task tracking record.

        Args:
            user: The user who uploaded the resume
            task_id: ID of the async task processing the resume

        Returns:
            The created task progress record
        """
        return ResumeProcessingTaskProgress.objects.create(
            task_id=task_id,
            user=user,
            task_type="resume_processing",
            status="pending",
            message="Preparing to process resume",
            current_step="file_path_resolved",
            progress_percent=0,
        )

    @staticmethod
    def get_task_status(task_id, user=None):
        """
        Get the status of a resume processing task.

        Args:
            task_id: ID of the task to get status for
            user: Optional user to filter by

        Returns:
            The task progress record, None if it doesn't exist, or a fallback from Django Q2
        """
        task_progress = None

        # First check if we have a progress record in the database
        try:
            if user:
                task_progress = ResumeProcessingTaskProgress.objects.get(
                    task_id=task_id, user=user
                )
            else:
                task_progress = ResumeProcessingTaskProgress.objects.get(
                    task_id=task_id
                )
            return task_progress
        except ResumeProcessingTaskProgress.DoesNotExist:
            # Fall back to checking Django Q2 result
            pass

        # Try to get result from Django Q2
        task_result = result(task_id)

        # If we got a result from Django Q2, return a synthetic progress record
        if task_result is not None:
            # Create a proper dummy task progress object
            return DummyTaskProgress(task_id, task_result)

        # If we didn't find anything, return None
        return None

    @staticmethod
    def update_task_progress(task_id, step_id, message=None):
        """
        Update the progress of a resume processing task.

        Args:
            task_id: ID of the task to update
            step_id: ID of the step that was completed
            message: Optional message to update

        Returns:
            The updated task progress record
        """
        task = ResumeProcessingTaskProgress.objects.get(task_id=task_id)
        task.mark_step_complete(step_id)

        if message:
            task.message = message
            task.save(update_fields=["message"])

        return task

    @staticmethod
    def fail_task(task_id, error_message):
        """
        Mark a resume processing task as failed.

        Args:
            task_id: ID of the task to mark as failed
            error_message: Error message explaining the failure

        Returns:
            The updated task progress record
        """
        task = ResumeProcessingTaskProgress.objects.get(task_id=task_id)
        task.status = "failed"
        task.message = error_message
        task.save(update_fields=["status", "message"])
        return task

    @staticmethod
    @transaction.atomic
    def update_profile_from_resume_data(user, resume_data):
        """
        Update a job seeker profile with data extracted from a resume.

        Args:
            user: The user to update the profile for
            resume_data: Dictionary of data extracted from the resume

        Returns:
            The updated job seeker profile
        """
        # Get or create the profile using ProfileManager
        profile = ProfileManager.get_profile(user)

        if not profile:
            # Create a new profile for this user
            profile = ProfileManager.create_or_update_profile(user, {})

        # Map resume data fields to profile fields
        field_mapping = {
            "skills": "skills",
            "experience": "experience",
            "education": "education",
            "certifications": "certifications",
            "years_of_experience": "years_of_experience",
            "current_title": "most_recent_title",
            "summary": "professional_summary",
            "phone": "phone",
            "location": "location",
            "resume_xml": "resume_xml",
        }

        # Update the profile with the resume data
        for resume_field, profile_field in field_mapping.items():
            if resume_field in resume_data and resume_data[resume_field]:
                # Special handling for skills (assume it's a list in resume_data)
                if resume_field == "skills" and isinstance(
                    resume_data[resume_field], list
                ):
                    skills_str = " | ".join(
                        skill.strip()
                        for skill in resume_data[resume_field]
                        if skill.strip()
                    )
                    setattr(profile, profile_field, skills_str)
                else:
                    setattr(profile, profile_field, resume_data[resume_field])

        profile.save()
        return profile

    @staticmethod
    def process_resume_batch_from_zip(
        recruiter: User,
        zip_file: UploadedFile,
        pool_name: str,
        job_opening_id: int | None = None,
    ) -> tuple[UploadedResumePool, list[str]]:
        """
        Process a batch of resumes from a ZIP file.

        Args:
            recruiter: The recruiter user who uploaded the ZIP file
            zip_file: The uploaded ZIP file containing resumes
            pool_name: Name for the resume pool
            job_opening_id: Optional job opening ID to associate with the pool

        Returns:
            Tuple of (created resume pool, list of task IDs for monitoring)
        """
        # Create the resume pool
        pool = UploadedResumePool.objects.create(
            recruiter=recruiter,
            name=pool_name,
        )

        # Set job opening if provided
        if job_opening_id:
            try:
                job_opening = JobOpening.objects.get(pk=job_opening_id)
                pool.job_opening = job_opening
                pool.save()
            except JobOpening.DoesNotExist:
                # Log but continue with processing
                print(f"Warning: Job opening with ID {job_opening_id} not found.")

        # Create temp directory for extracted files
        temp_dir = tempfile.mkdtemp(prefix="resume_batch_")
        task_ids = []

        try:
            # Extract ZIP file
            with ZipFile(zip_file, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            # Process each resume file
            for root, _, files in os.walk(temp_dir):
                for filename in files:
                    # Only process PDF files (common resume format)
                    if filename.lower().endswith(".pdf"):
                        file_path = os.path.join(root, filename)

                        # Generate a task ID
                        task_id = str(uuid.uuid4())

                        # Queue the resume processing task
                        async_task(
                            "apps.job_seekers.tasks.process_resume_for_pool",
                            file_path,
                            pool.pk,
                            task_id,
                            hook="apps.job_seekers.tasks.cleanup_temp_resume_file",
                        )

                        task_ids.append(task_id)
        except Exception as e:
            # Log the error but don't re-raise
            print(f"Error processing ZIP file: {str(e)}")
            # Clean up temp directory in case of error
            shutil.rmtree(temp_dir, ignore_errors=True)
            # Return the pool and empty task list
            return pool, []

        return pool, task_ids
