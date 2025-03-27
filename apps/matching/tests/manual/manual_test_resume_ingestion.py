"""
Manual test for ingesting resumes and creating talent sheets.

This script demonstrates how to use the ingest_resumes command
with the new --join_talent_pool option.

Usage:
    1. This script will use resume PDFs in sample_data/resumes
    2. Run this script to ingest them and create talent sheets
    3. Observe the output and talent sheets created
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
    print_header("HIREDAR RESUME INGESTION TEST")
    print(
        "\nThis script will ingest resume PDFs and create talent sheets from sample_data/resumes"
    )

    # Use the sample data directory
    resume_dir = "sample_data/resumes"
    resume_path = Path(resume_dir)

    if not resume_path.exists() or not resume_path.is_dir():
        print(f"Error: Sample resume directory {resume_dir} not found")
        print("Please make sure the directory exists and contains resume PDFs")
        return 1

    pdf_files = list(resume_path.glob("*.pdf"))
    if not pdf_files:
        print(f"Error: No PDF files found in {resume_dir}")
        return 1

    print(f"Found {len(pdf_files)} PDF files in {resume_dir}")

    # Ask if should join talent pool
    join_pool = (
        input("Add job seekers to talent pool? (y/n, default: y): ").lower() != "n"
    )

    # Ask about limit
    use_limit = (
        input("Limit number of resumes to process? (y/n, default: y): ").lower() != "n"
    )
    limit = 5  # Default to 5 resumes for faster testing
    if use_limit:
        try:
            limit_input = input(
                f"How many resumes to process (1-{len(pdf_files)}, default: 5): "
            )
            if limit_input:
                limit = int(limit_input)
                limit = max(1, min(limit, len(pdf_files)))  # Ensure within range
        except ValueError:
            print("Invalid number, using default limit of 5 resumes")
    else:
        limit = None

    verbosity = input("Verbosity level (1-3, default 1): ") or "1"

    # Prepare command
    cmd = ["python", "manage.py", "ingest_resumes", resume_dir, "-v", verbosity]

    if join_pool:
        cmd.append("--join_talent_pool")

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

        if process.returncode == 0 and join_pool:
            print_header("NEXT STEPS")
            print("1. Create talent embeddings:")
            print("   python manage.py create_talent_embeddings --all")
            print("\n2. Post job openings:")
            print("   python manage.py post_job_openings --activate")
            print("\n3. Generate matches:")
            print("   python manage.py create_candidate_matches --all")
            print("\nOr run the end-to-end test script:")
            print(
                "python apps/matching/tests/manual/manual_test_end_to_end_matching.py"
            )

    except subprocess.CalledProcessError as e:
        print(f"\nCommand failed with exit code {e.returncode}")
        return e.returncode

    return 0


if __name__ == "__main__":
    sys.exit(main())
