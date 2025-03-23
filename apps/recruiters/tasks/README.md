# Recruiter Tasks

This directory contains asynchronous task functions for the recruiters app, designed to work with Django Q.

## Overview

These tasks handle various asynchronous operations related to recruiters, such as:

- Processing job descriptions
- Creating job openings from text
- Handling post-processing callbacks

## Task Structure

Tasks are organized by functionality:

- `job_processing_tasks.py`: Tasks related to processing job descriptions and creating job openings

## Usage

Tasks are typically queued using Django Q's `async_task` function:

```python
from django_q.tasks import async_task

# Queue a task to process a job description
async_task(
    "apps.recruiters.tasks.process_job_description",
    task_id,
    job_title,
    job_description,
    recruiter_profile_id,
    hook="apps.recruiters.tasks.job_processing_done",
)
```

## Hooks

Hooks are callback functions that are executed after a task completes:

- `job_processing_done`: Called after job processing completes (success or failure)

## Task Pipeline

The job processing pipeline follows these steps:

1. Pre-process the job description text
2. Convert the text to structured XML using LLM
3. Parse the XML to extract structured data
4. Create a new JobOpening from the extracted data
5. Execute hook function with processing results
