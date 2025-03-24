# Job Seekers Tasks

This directory contains asynchronous tasks for the job_seekers app, organized by functional area.

## Architecture

The tasks are organized following these principles:

1. **Separation of Concerns**: Tasks are divided into logical functional groups
2. **Task Chaining with Hooks**: We use the "hook" mechanism to trigger follow-up tasks
3. **Parallel Processing**: Multiple tasks can run in parallel after a primary task completes

## Task Structure

- **resume_processing_tasks.py**: Tasks for resume upload and processing
- **cleanup_tasks.py**: Tasks for cleaning up temporary data and records
- **recommendation_tasks.py**: Tasks for generating role recommendations and personal taglines
- **hooks.py**: Hook functions for task chaining

## Task Flow

The primary task flow is:

1. **User uploads a resume** → triggers `handle_resume_upload_task`
2. **Resume processing completes** → triggers `resume_processing_completed` hook
3. **Hook starts multiple tasks** in parallel:
   - `generate_role_recommendations`
   - `generate_personal_tagline`
4. **All tasks complete** → potentially triggers `all_processing_complete` hook

## Implementation Details

### Hooks

Hooks are used to chain tasks together without making individual tasks aware of the complete workflow. This provides:

- Cleaner separation of concerns
- More flexibility to change workflow steps
- Ability to handle failures gracefully

### Task Groups

Tasks that are logically related are grouped together with a common `group` parameter.

### Error Handling

Each task:

- Returns structured response objects
- Handles errors independently
- Logs all activities for traceability

## Adding New Tasks

When adding new tasks:

1. Identify which group it belongs to (or create a new module)
2. Follow the established pattern for parameter and return types
3. Handle errors gracefully
4. Update the `__init__.py` to export the new task
5. Update this README if adding a new task category
