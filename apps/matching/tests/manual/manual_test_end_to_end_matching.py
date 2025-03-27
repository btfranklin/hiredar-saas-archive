"""
End-to-end manual test for the job matching system.

This script guides the user through testing the complete matching process:
1. Ingesting resumes
2. Creating talent sheets and embeddings
3. Posting job openings from sample data
4. Creating job embeddings
5. Generating matches

This demonstrates the complete flow of the matching system with real data.
"""

import os
import subprocess
import sys
import time
from pathlib import Path


def print_header(title):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)


def print_step(number, total, description):
    """Print a step indicator."""
    print(f"\n[STEP {number}/{total}] {description}")
    print("-" * 60)


def run_command(cmd, description=None):
    """Run a command and return its exit code."""
    if description:
        print(f"\n{description}")

    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)

    try:
        process = subprocess.run(cmd, check=True)
        print("-" * 60)
        print(f"Command completed with exit code {process.returncode}")
        return process.returncode
    except subprocess.CalledProcessError as e:
        print("-" * 60)
        print(f"Command failed with exit code {e.returncode}")
        return e.returncode


def wait_for_user():
    """Wait for user to press Enter before continuing."""
    input("\nPress Enter to continue to the next step...")


def main():
    """Execute the end-to-end test flow."""
    total_steps = 5

    print_header("HIREDAR MATCHING SYSTEM END-TO-END TEST")
    print("\nThis script will guide you through testing the complete matching process")
    print("Using sample data from:")
    print("- Resumes: sample_data/resumes")
    print("- Job openings: sample_data/job_openings")
    print(
        "\nThe test will create test users, talent sheets, and job matches in the system."
    )

    # Set default verbosity
    verbosity = input("\nVerbosity level for all commands (1-3, default 1): ") or "1"

    wait_for_user()

    # Step 1: Ingest resumes
    print_step(1, total_steps, "INGEST RESUMES")
    print("Now we'll ingest resume PDFs and create talent sheets")

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

    # Ask if user wants to limit the number of resumes
    use_limit = (
        input("Limit number of resumes to process? (y/n, default: y): ").lower() != "n"
    )
    resume_limit = 5  # Default to 5 resumes for faster testing
    if use_limit:
        try:
            limit_input = input(
                f"How many resumes to process (1-{len(pdf_files)}, default: 5): "
            )
            if limit_input:
                resume_limit = int(limit_input)
                resume_limit = max(
                    1, min(resume_limit, len(pdf_files))
                )  # Ensure within range
        except ValueError:
            print("Invalid number, using default limit of 5 resumes")
    else:
        resume_limit = None

    # Run ingest_resumes with talent pool option
    cmd = [
        "python",
        "manage.py",
        "ingest_resumes",
        resume_dir,
        "--join_talent_pool",
        "-v",
        verbosity,
    ]

    if resume_limit:
        cmd.append("--limit")
        cmd.append(str(resume_limit))

    if run_command(cmd, "Ingesting resumes and creating talent sheets") != 0:
        if (
            not input("\nResume ingestion failed. Continue anyway? (y/n): ")
            .lower()
            .startswith("y")
        ):
            return 1

    wait_for_user()

    # Step 2: Create talent embeddings
    print_step(2, total_steps, "CREATE TALENT EMBEDDINGS")
    print("Now we'll create vector embeddings for the talent sheets")

    cmd = ["python", "manage.py", "create_talent_embeddings", "--all", "-v", verbosity]

    if run_command(cmd, "Creating talent sheet embeddings") != 0:
        if (
            not input("\nEmbedding creation failed. Continue anyway? (y/n): ")
            .lower()
            .startswith("y")
        ):
            return 1

    wait_for_user()

    # Step 3: Import job data
    print_step(3, total_steps, "POST JOB OPENINGS")
    print("Now we'll post job openings from sample data")

    # Ask if jobs should be activated and limited
    use_activate = (
        input("Automatically activate jobs after posting? (y/n, default: y): ").lower()
        != "n"
    )

    job_limit = None
    use_job_limit = (
        input("Limit number of jobs to post? (y/n, default: y): ").lower() != "n"
    )
    if use_job_limit:
        try:
            job_dir = Path("sample_data/job_openings")
            job_files = list(job_dir.glob("*.md"))
            job_count = len(job_files)

            limit_input = input(f"How many jobs to post (1-{job_count}, default: 3): ")
            if limit_input:
                job_limit = int(limit_input)
                job_limit = max(1, min(job_limit, job_count))
            else:
                job_limit = 3  # Default to 3 jobs for faster testing
        except (ValueError, FileNotFoundError):
            print("Error determining job count, using default limit of 3 jobs")
            job_limit = 3

    cmd = ["python", "manage.py", "post_job_openings", "-v", verbosity]

    if use_activate:
        cmd.append("--activate")

    if job_limit:
        cmd.append("--limit")
        cmd.append(str(job_limit))

    if run_command(cmd, "Posting job openings") != 0:
        if (
            not input("\nJob posting failed. Continue anyway? (y/n): ")
            .lower()
            .startswith("y")
        ):
            return 1

    wait_for_user()

    # Step 4: Create job embeddings
    print_step(4, total_steps, "CREATE JOB EMBEDDINGS")
    print("Now we'll create vector embeddings for the job openings")

    # Only need to create embeddings if jobs weren't already activated
    if not use_activate:
        cmd = ["python", "manage.py", "create_job_embeddings", "--all", "-v", verbosity]

        if run_command(cmd, "Creating job embeddings") != 0:
            if (
                not input("\nJob embedding creation failed. Continue anyway? (y/n): ")
                .lower()
                .startswith("y")
            ):
                return 1
    else:
        print("Job embeddings were already created when jobs were activated")

    wait_for_user()

    # Step 5: Generate matches
    print_step(5, total_steps, "GENERATE MATCHES")
    print("Finally, we'll generate matches between talent sheets and job openings")

    cmd = ["python", "manage.py", "create_candidate_matches", "--all", "-v", verbosity]

    if run_command(cmd, "Generating matches") != 0:
        print("\nMatch generation failed.")
        return 1

    # Final summary
    print_header("MATCHING PROCESS COMPLETE")
    print("\nThe matching process has completed successfully!")
    print("\nYou can now:")
    print("1. Check the matches in the admin interface")
    print("2. Review job openings and their matched candidates")
    print("3. Review talent sheets and their matched job openings")

    print("\nAdditional commands you might find useful:")
    print("- python manage.py delete_job_embeddings --all")
    print("- python manage.py delete_talent_embeddings --all")
    print("- python manage.py flush_matches")

    return 0


if __name__ == "__main__":
    sys.exit(main())
