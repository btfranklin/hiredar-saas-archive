"""
Manual test for posting job openings from sample data.

This script demonstrates how to use the post_job_openings command
to create job openings from markdown files.

Usage:
    1. Make sure sample_data/job_openings contains markdown files
    2. Run this script
    3. Observe the output and follow prompts
"""

import os
import subprocess
import sys
from pathlib import Path


def print_header(title):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)


def main():
    """Execute the main test flow."""
    print_header("HIREDAR JOB POSTING TEST")
    print(
        "\nThis script will post job openings from markdown files in sample_data/job_openings."
    )

    # Check if sample data exists
    sample_dir = Path("sample_data/job_openings")
    if not sample_dir.exists() or not sample_dir.is_dir():
        print(f"Error: {sample_dir} directory not found")
        return 1

    md_files = list(sample_dir.glob("*.md"))
    if not md_files:
        print(f"Error: No markdown files found in {sample_dir}")
        return 1

    print(f"Found {len(md_files)} markdown job files in {sample_dir}")

    # Ask if jobs should be activated
    activate = (
        input("Activate job openings after posting? (y/n, default: y): ").lower() != "n"
    )

    # Ask about limit
    use_limit = (
        input("Limit number of jobs to post? (y/n, default: y): ").lower() != "n"
    )
    limit = 3  # Default to 3 jobs for faster testing
    if use_limit:
        try:
            limit_input = input(
                f"How many jobs to post (1-{len(md_files)}, default: 3): "
            )
            if limit_input:
                limit = int(limit_input)
                limit = max(1, min(limit, len(md_files)))  # Ensure within range
        except ValueError:
            print("Invalid number, using default limit of 3 jobs")
    else:
        limit = None

    verbosity = input("Verbosity level (1-3, default 1): ") or "1"

    # Prepare command
    cmd = ["python", "manage.py", "post_job_openings", "-v", verbosity]

    if activate:
        cmd.append("--activate")

    if limit:
        cmd.append("--limit")
        cmd.append(str(limit))

    # Display command
    print("\nRunning command:")
    print(" ".join(cmd))
    print("\n" + "=" * 60)

    # Execute command
    try:
        process = subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print(f"Command completed with exit code {process.returncode}")

        if process.returncode == 0:
            print_header("NEXT STEPS")

            if activate:
                print("1. Generate matches with job seekers:")
                print("   - First ingest resumes with:")
                print(
                    "     python manage.py ingest_resumes sample_data/resumes --join_talent_pool"
                )
                print("   - Then create talent embeddings:")
                print("     python manage.py create_talent_embeddings --all")
                print("   - Finally generate matches:")
                print("     python manage.py create_candidate_matches --all")
            else:
                print("1. Activate job openings:")
                print("   - Run 'python manage.py post_job_openings --activate'")
                print("   - Or activate individual jobs in the admin interface")
                print("\n2. After activation, generate matches by:")
                print("   - Ingesting resumes with:")
                print(
                    "     python manage.py ingest_resumes sample_data/resumes --join_talent_pool"
                )
                print("   - Creating talent embeddings:")
                print("     python manage.py create_talent_embeddings --all")
                print("   - Generating matches:")
                print("     python manage.py create_candidate_matches --all")

            print("\nOr run the end-to-end test script:")
            print(
                "python apps/matching/tests/manual/manual_test_end_to_end_matching.py"
            )

            return 0
        else:
            return process.returncode

    except subprocess.CalledProcessError as e:
        print(f"\nCommand failed with exit code {e.returncode}")
        return e.returncode


if __name__ == "__main__":
    sys.exit(main())
