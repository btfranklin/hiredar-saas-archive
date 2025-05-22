# Recruiter Tasks

This directory contains asynchronous task functions for the recruiters app, designed to work with Django Q.

## Overview

These tasks handle various asynchronous operations related to recruiters, such as:

- Processing job descriptions and creating job openings
- Handling task completion callbacks
- Managing processing status updates

## Task Structure

Tasks are organized by functionality:

- `job_processing_tasks.py`: Tasks related to processing job descriptions and creating job openings
- `hooks.py`: Hook functions that are executed after tasks complete (for task chaining)

## Architecture

The task architecture follows a pattern aligned with the job seekers app:

1. **Task Entry Points**: Functions in this directory serve as entry points for Django Q
2. **Implementation Logic**: The actual implementation logic resides in the `utils` directory
3. **Hook Functions**: Callbacks in `hooks.py` handle task completion and chaining
4. **Clear Responsibility Separation**: Tasks handle basic validation and call implementations

## Usage

Tasks are typically queued using Django Q's `async_task` function:

```python
from apps.core.tasks import safe_async_task as async_task

# Queue a task to process a job description with high priority
async_task(
    "apps.recruiters.tasks.handle_job_description_task",
    task_id,
    job_title,
    job_description,
    recruiter_profile_id,
    hook="apps.recruiters.tasks.hooks.job_processing_done",
    queue="high",
)
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
