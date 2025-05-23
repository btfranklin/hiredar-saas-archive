# Recruiter Tasks

This directory contains asynchronous task functions for the recruiters app, designed to work with Celery.

## Overview

The recruiter tasks handle background processing for recruiter-specific operations, including:

- Job description processing and XML conversion
- Bulk resume upload and processing
- Credit management and billing operations
- Candidate matching and analysis

## Task Organization

Tasks are organized by functional area:

- `job_processing_tasks.py`: Tasks for processing job descriptions
- `bulk_resume_tasks.py`: Tasks for handling bulk resume uploads
- `credit_tasks.py`: Tasks for credit management and billing

## Usage Patterns

1. **Task Entry Points**: Functions in this directory serve as entry points for Celery
   workers and should handle all necessary error checking and logging.

2. **Database Operations**: Tasks should use appropriate database transactions
   and handle potential race conditions when updating shared resources.

3. **Error Handling**: All tasks should include comprehensive error handling
   and logging to facilitate debugging and monitoring.

Tasks are typically queued using Celery's task decorators:

```python
from apps.core.tasks import safe_async_task

safe_async_task(process_job_description, job_id, user_id)
```

## Task Functions

### `handle_job_description_task`

Processes a job description text and creates a structured job opening:

1. Validates the recruiter profile exists
2. Calls the implementation in `utils.job_processing.pipeline`
3. Returns a structured result with status and job ID

## Hook Functions

### `job_processing_done`

Callback function executed after job processing completes:

1. Validates the task completed successfully
2. Logs success or failure
3. Can be expanded to trigger follow-up tasks, such as candidate matching

## Pipeline Flow

The job processing follows these steps:

1. Task validation and setup
2. Delegation to implementation in the utils module
3. Processing of text into structured data
4. Creation of a job opening
5. Execution of hook function with processing results

## Bulk Upload Pipeline

The bulk upload pipeline manages processing of ZIP archives containing multiple resumes.

### `unpack_and_process_zip`

1. Marks the placeholder TaskMeta as RUNNING
2. Unpacks the ZIP, filters valid resume files, and creates `ResumeFile` records
3. For each resume file:
   - Creates a `TaskMeta` entry for per-resume progress
   - Schedules `process_resume_for_pool` on the default queue with a cleanup hook
4. Marks the placeholder TaskMeta as SUCCESS and the bulk upload as processed

The helper `cleanup_temp_resume_file` is used as a hook to delete temporary files after processing.
