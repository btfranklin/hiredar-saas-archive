# Hiredar Scheduled Tasks

This document describes the scheduled tasks in the Hiredar application and how they are managed.

## Overview

Hiredar uses Django Q for scheduling and running background tasks. These tasks handle processes that should run periodically without user intervention, such as cleanup operations, data refreshes, or other maintenance tasks.

## Task Types and Schedules

The following scheduled tasks are configured in the system:

| Task | Function | Schedule | Description |
|------|----------|----------|-------------|
| Resume Processing Cleanup | `apps.job_seekers.tasks.cleanup_tasks.cleanup_resume_processing_progress` | Every 15 minutes | Cleans up completed and old resume processing task records |

## Management & Troubleshooting

### Viewing Scheduled Tasks

To view all scheduled tasks in the system, use the Django admin interface:

1. Navigate to `/admin/django_q/schedule/`
2. Review the list of scheduled tasks

### Command Line Management

The system includes command-line tools for managing scheduled tasks:

```bash
# Check and fix cleanup schedule issues
python manage.py fix_cleanup_schedule

# Reset cleanup schedule to run exactly every 15 minutes
python manage.py reset_cleanup_schedule

# View task status
python manage.py qmonitor
```

### Task Scheduling Mechanics

Task scheduling is handled through several components:

1. **App Config**: Tasks are registered during application startup in `apps.py`
2. **Middleware**: A middleware component ensures tasks are only scheduled once
3. **Cache System**: A cache-based coordination system prevents multiple processes from creating duplicate schedules
4. **Maintenance Commands**: Command-line tools allow for manual intervention

## Resume Processing Cleanup Details

The resume processing cleanup task handles temporary records created during the resume processing flow:

### Schedule Details

- **Frequency**: Runs every 15 minutes
- **Function**: `apps.job_seekers.tasks.cleanup_tasks.cleanup_resume_processing_progress`
- **Cache Key**: `job_seekers_cleanup_task_scheduled`

### Cleanup Policies

The task applies the following cleanup policies:

1. **Completed Records**: Any completed or failed resume processing records older than 5 minutes are deleted
2. **Old Records**: All resume processing records older than 7 days are deleted regardless of status

### Troubleshooting Issues

If you encounter issues with tasks running too frequently or not at all:

1. Check for multiple schedule entries with the same name:

   ```bash
   python manage.py fix_cleanup_schedule
   ```

2. If issues persist, reset the schedule:

   ```bash
   python manage.py reset_cleanup_schedule
   ```

3. For debugging task execution, check the logs:

   ```bash
   tail -f logs/django-q.log
   ```

## Adding New Scheduled Tasks

To add a new scheduled task:

1. Define the task function in an appropriate app module
2. Create a scheduling function similar to `ensure_cleanup_scheduled` in the relevant app
3. Connect the scheduling function to an appropriate trigger (app startup, signal, etc.)
4. Add documentation for the new task in this file

## Technical Implementation

The scheduling system uses a combination of Django's app configuration, middleware, and cache to ensure tasks are properly scheduled:

```python
# Example from apps/job_seekers/tasks/cleanup_tasks.py
def ensure_cleanup_scheduled() -> None:
    """
    Ensure the cleanup task is scheduled.
    """
    # Use cache to prevent multiple processes from scheduling simultaneously
    cache_key = "job_seekers_cleanup_task_scheduled"
    if cache.get(cache_key):
        return
        
    try:
        # Check for existing valid schedules
        # Create if needed
        # Set cache flag to prevent repeats
        cache.set(cache_key, True, 60 * 60)  # Cache for an hour
    except Exception as e:
        logger.error("Failed to schedule cleanup task: %s", e)
```

This approach ensures that even in a multi-process environment, tasks are only scheduled once.
