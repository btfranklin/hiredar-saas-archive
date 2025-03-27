# Manual Tests for Matching System

This directory contains manual test scripts for the Hiredar matching system. These tests are designed to be run manually with explicit user interaction, allowing for testing of complex end-to-end flows.

## Available Tests

### 1. Resume Ingestion Test (`manual_test_resume_ingestion.py`)

A simple test to demonstrate using the enhanced `ingest_resumes` command with the new `--join_talent_pool` option.

**Usage:**
```bash
python apps/matching/tests/manual/manual_test_resume_ingestion.py
```

### 2. Job Posting Test (`manual_test_post_job_openings.py`)

A simple test to demonstrate using the `post_job_openings` command to create job openings from sample markdown files.

**Usage:**
```bash
python apps/matching/tests/manual/manual_test_post_job_openings.py
```

### 3. End-to-End Matching Test (`manual_test_end_to_end_matching.py`)

A comprehensive test that guides through the entire matching process:
- Ingesting resumes
- Creating talent sheets and embeddings
- Posting job openings from sample data
- Creating job embeddings
- Generating matches

This demonstrates the complete flow of the matching system with real data.

**Usage:**
```bash
python apps/matching/tests/manual/manual_test_end_to_end_matching.py
```

## Prerequisites

To run these tests, you'll need:

1. A local development environment set up with the Hiredar project
2. Database migrations applied
3. A directory containing sample resume PDFs
4. Sample job markdown files (provided in `sample_data/job_openings`)

## Running the Tests

1. Make sure you're in the project root directory
2. Run the desired test script using Python
3. Follow the prompts in the interactive test script

## Notes

- These tests will create actual data in your development database
- To clean up test data:
  - Delete job embeddings: `python manage.py delete_job_embeddings --all`
  - Delete talent embeddings: `python manage.py delete_talent_embeddings --all`
  - Delete matches: `python manage.py flush_matches`
  - For complete cleanup, you may need to delete users and other related data manually

## Available Commands

These tests utilize the following management commands:

- `ingest_resumes`: Ingest resume PDFs and create test job seekers
- `create_talent_embeddings`: Create embeddings for talent sheets
- `post_job_openings`: Create test recruiter and post job openings from markdown files
- `create_job_embeddings`: Create embeddings for job openings
- `generate_matches`: Generate candidate matches between talent and jobs
- `flush_matches`: Delete all candidate matches from the system 