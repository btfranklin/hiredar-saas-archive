# Job Seekers Tasks - Pure Celery Implementation

This document describes the Celery tasks in the job_seekers app that have been fully converted from legacy hook-based patterns to pure Celery implementations.

## Architecture

All tasks now follow pure Celery patterns with:
- **Consistent return values**: All tasks return `{"status": "success|error|skipped", "message": "...", ...}`
- **Semantic naming**: All tasks use descriptive names like `generate_talent_sheet_{profile_id}`
- **Proper chaining**: Uses native Celery `chain()`, `group()`, and `chord()` primitives
- **Structured data flow**: Tasks return dictionaries that can be consumed by subsequent tasks

## Task Overview

### 1. Resume Processing Completion
- **Task**: `resume_processing_completed`
- **File**: `apps/job_seekers/tasks/hooks.py`
- **Purpose**: Coordinates follow-up tasks after successful resume processing
- **Triggers**: Called as part of resume processing chains in `resume_processing_views.py`
- **Chains to**: `generate_role_recommendations` for user-owned profiles

### 2. Role Recommendations
- **Task**: `generate_role_recommendations`  
- **File**: `apps/job_seekers/tasks/recommendation_tasks.py`
- **Purpose**: Generates AI-powered role recommendations from resume XML
- **Input flexibility**: Handles `dict`, `int`, or `None` inputs for chain compatibility
- **Idempotency**: Deletes and recreates recommendations on each run

### 3. Talent Sheet Generation
- **Task**: `generate_talent_sheet_task`
- **File**: `apps/job_seekers/tasks/talent_sheet_tasks.py`  
- **Purpose**: Creates LLM-generated talent sheets for job seekers
- **Triggers**: Admin actions, talent pool toggles, pool resume processing
- **Idempotency**: Skips if talent sheet already exists

### 4. Personal Tagline Generation
- **Task**: `generate_personal_tagline`
- **File**: `apps/job_seekers/tasks/personal_tagline_tasks.py`
- **Purpose**: Creates concise professional taglines from resume data
- **Idempotency**: Overwrites existing taglines (last write wins)

### 5. Pool Processing Tasks
- **Tasks**: `process_resume_for_pool`, `cleanup_temp_resume_file`
- **File**: `apps/job_seekers/tasks/pool_tasks.py`
- **Purpose**: Process resumes for candidate pools and clean up temporary files
- **Chain pattern**: Used together in bulk resume processing workflows

## Current Celery Usage Patterns

### Chain Example (Resume Processing)
```python
from celery import chain

task_chain = chain(
    handle_resume_upload_task.si(file_path, profile_id, task_id=task_id),
    resume_processing_completed.s()
)
async_result = task_chain.apply_async(task_id=f"resume_processing_chain_{profile_id}_{timestamp}")
```

### Chain Example (Pool Processing)  
```python
from celery import chain

process_task = process_resume_for_pool.si(local_path, pool_id, bulk_pk, meta_pk)
cleanup_task = cleanup_temp_resume_file.s()

task_chain = chain(process_task, cleanup_task)
async_result = task_chain.apply_async(task_id=f"candidate_pool_process_{task_id}")
```

### Single Task Example
```python
async_task(
    generate_talent_sheet_task,
    profile.pk,
    task_name=f"generate_talent_sheet_{profile.pk}"
)
```
