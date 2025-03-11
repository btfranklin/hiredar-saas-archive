#!/usr/bin/env python
"""
Script to batch ingest resume PDFs into the Hiredar system for testing purposes.

This script deliberately uses a non-standard import organization because
Django and application imports must happen after path setup and Django initialization.
"""

# pylint: disable=wrong-import-position,wrong-import-order

# Standard library imports
import argparse
import os
import sys
import traceback
import uuid
from pathlib import Path

# Add the project root to the Python path BEFORE importing Django modules
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Set Django settings environment variable
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hiredar.settings")

# Initialize Django
import django

django.setup()

# Now that Django is set up and the path includes the project root, we can import Django modules
from django.conf import settings  # noqa: E402
from django.core.files.base import ContentFile  # noqa: E402
from django.core.files.storage import default_storage  # noqa: E402

# Local application imports - must come after Django initialization
from apps.authentication.models import User  # noqa: E402
from apps.job_seekers.models import JobSeekerProfile  # noqa: E402
from apps.job_seekers.utils.llm_api import convert_text_resume_to_xml  # noqa: E402
from apps.job_seekers.utils.resume_parser import (  # noqa: E402
    extract_text_from_pdf,
    update_profile_from_xml,
)

# Check if the OpenAI API key is set
if "OPENAI_API_KEY" not in os.environ and not hasattr(settings, "OPENAI_API_KEY"):
    print("WARNING: OPENAI_API_KEY environment variable is not set.")
    print("The resume processing may fail when calling the OpenAI API.")


def create_test_user(counter: int) -> tuple[User, JobSeekerProfile] | tuple[None, None]:
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
        # Use the UserManager's create_user method which handles username generation
        # The linter might not recognize this method, but it definitely exists
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
        print(f"Error creating test user: {e}")
        traceback.print_exc()
        return None, None


def process_resume(resume_path: str, profile: JobSeekerProfile) -> bool:
    """
    Process a resume file and update the given profile with extracted information.

    Args:
        resume_path: Path to the resume file
        profile: JobSeekerProfile to update

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
            print(f"  - ERROR reading file: {str(e)}")
            return False

        # Step 2: Save the resume temporarily
        temp_dir = "resumes"
        # Make sure the directory exists
        os.makedirs(os.path.join(settings.MEDIA_ROOT, temp_dir), exist_ok=True)

        temp_path = f"{temp_dir}/temp_{uuid.uuid4().hex}.pdf"
        saved_path = default_storage.save(temp_path, ContentFile(file_content))
        physical_path = default_storage.path(saved_path)

        print(f"Processing resume: {os.path.basename(resume_path)}")

        # Step 3: Extract text from the PDF
        print("  - Extracting text from PDF...")
        resume_text = extract_text_from_pdf(physical_path)

        if not resume_text:
            print("  - ERROR: Could not extract text from PDF")
            default_storage.delete(saved_path)
            return False

        # Step 4: Convert to XML using LLM
        print("  - Converting to structured XML using LLM...")
        xml_content = convert_text_resume_to_xml(resume_text)

        if not xml_content:
            print("  - ERROR: Could not convert resume to XML")
            default_storage.delete(saved_path)
            return False

        # Step 5: Extract information from XML and update profile
        print("  - Extracting information and updating profile...")
        update_profile_from_xml(profile, xml_content)

        # Step 6: Clean up
        default_storage.delete(saved_path)

        print("  - SUCCESS: Profile updated successfully")
        return True

    except Exception as e:
        print(f"  - ERROR: {str(e)}")
        traceback.print_exc()
        # Clean up if needed
        if saved_path:
            try:
                default_storage.delete(saved_path)
            except Exception:
                pass
        return False


def ingest_resumes(directory_path: str) -> None:
    """
    Process all resumes in the given directory.

    Args:
        directory_path: Path to directory containing resume files
    """
    resume_dir = Path(directory_path)

    if not resume_dir.exists() or not resume_dir.is_dir():
        print(f"Error: {directory_path} is not a valid directory")
        return

    # Get all PDF files in the directory
    resume_files = list(resume_dir.glob("*.pdf"))

    if not resume_files:
        print(f"No PDF files found in {directory_path}")
        return

    print(f"Found {len(resume_files)} resume files to process")

    # Process each resume
    success_count = 0
    failure_count = 0

    for i, resume_file in enumerate(resume_files, 1):
        print(f"\n[{i}/{len(resume_files)}] Processing: {resume_file.name}")

        # Create a test user for this resume
        user, profile = create_test_user(i)

        if not user or not profile:
            print(f"  - Failed to create user for resume {resume_file.name}")
            failure_count += 1
            continue

        # Process the resume and update the profile
        success = process_resume(str(resume_file), profile)

        if success:
            success_count += 1
            print(f"✅ Successfully processed resume for {user.email}")
            # Display some key information from the profile
            print(f"  - Current position: {profile.current_position}")
            print(f"  - Years of experience: {profile.years_of_experience}")
            skills_display = (
                ", ".join(profile.skills_list[:5]) if profile.skills_list else "None"
            )
            if len(profile.skills_list) > 5:
                skills_display += "..."
            print(f"  - Skills: {skills_display}")
        else:
            failure_count += 1
            print(f"❌ Failed to process resume for {user.email}")

    # Print summary at the end
    print("\n" + "=" * 50)
    print(f"SUMMARY: Processed {len(resume_files)} resumes")
    print(f"SUCCESS: {success_count} resumes")
    print(f"FAILURE: {failure_count} resumes")
    print("=" * 50)


def main() -> None:
    """Main function to parse arguments and run the script."""
    parser = argparse.ArgumentParser(description="Ingest resumes from a directory")
    parser.add_argument("directory", help="Directory containing resume files (PDF)")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    # Set verbosity
    if args.verbose:
        print("Verbose mode enabled")

    try:
        ingest_resumes(args.directory)
    except KeyboardInterrupt:
        print("\nScript interrupted by user. Exiting...")
        sys.exit(1)
    except Exception as e:
        print(f"Unhandled error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
