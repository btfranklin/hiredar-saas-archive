# Hiredar Scheduled Tasks

This document describes the scheduled tasks in the Hiredar application and how they are managed using Celery Beat.

## Overview

Hiredar uses Celery Beat for scheduling and running periodic background tasks. These tasks handle processes that should run automatically at regular intervals, such as cleanup operations, data refreshes, or other maintenance tasks.

## Task Configuration

Scheduled tasks are configured in the Django settings file using the `CELERY_BEAT_SCHEDULE` setting. This provides a clean, centralized way to manage all periodic tasks.

## Current Scheduled Tasks

The following scheduled tasks are configured in the system:

| Task | Function | Schedule | Description |
|------|----------|----------|-------------|
| Resume Processing Cleanup | `apps.resume_processing.tasks.cleanup_tasks.cleanup_resume_processing_progress` | Every 15 minutes | Cleans up completed and old resume processing task records |

## Management & Troubleshooting

### Viewing Scheduled Tasks

To view all scheduled tasks in the system:

1. **Settings Configuration**: Check the `CELERY_BEAT_SCHEDULE` setting in `hiredar/settings.py`
2. **Django Admin**: If using `django-celery-beat`, navigate to `/admin/django_celery_beat/periodictask/`
3. **Command Line**: Use Celery inspection commands to view active schedules

### Running Celery Beat

To start the Celery Beat scheduler:

```bash
# In development
celery -A hiredar beat --loglevel=info

# In production (typically run as a service)
celery -A hiredar beat --loglevel=info --detach
```

### Command Line Management

Manual cleanup can still be performed using the task directly:

```bash
# Run cleanup manually
python manage.py shell -c "from apps.resume_processing.tasks.cleanup_tasks import cleanup_resume_processing_progress; cleanup_resume_processing_progress()"
```

## Resume Processing Cleanup Details

The resume processing cleanup task handles temporary records created during the resume processing flow:

### Schedule Details

- **Frequency**: Runs every 15 minutes (900 seconds)
- **Function**: `cleanup_resume_processing_progress`
- **Queue**: `default`
- **Task Name**: `apps.resume_processing.tasks.cleanup_tasks.cleanup_resume_processing_progress`

### Cleanup Policies

The task applies the following cleanup policies:

1. **Completed Records**: Any completed or failed resume processing records older than 5 minutes are deleted
2. **Old Records**: All resume processing records older than 7 days are deleted regardless of status

### Task Return Values

The cleanup task returns structured data:

```python
{
    "status": "success|error",
    "message": "Cleanup summary",
    "completed_records": 5,  # Number of completed records cleaned
    "old_records": 2,        # Number of old records cleaned
}
```

## Adding New Scheduled Tasks

To add a new scheduled task:

1. **Create the task function** with `@shared_task` decorator:

   ```python
   from celery import shared_task

   @shared_task(name="apps.myapp.tasks.my_scheduled_task")
   def my_scheduled_task() -> dict[str, Any]:
       # Task implementation
       return {"status": "success", "message": "Task completed"}
   ```

2. **Add to CELERY_BEAT_SCHEDULE** in `hiredar/settings.py`:

   ```python
   CELERY_BEAT_SCHEDULE = {
       "my-scheduled-task": {
           "task": "apps.myapp.tasks.my_scheduled_task",
           "schedule": 3600.0,  # Every hour
           "options": {
               "queue": "default",
           },
       },
   }
   ```

3. **Update documentation** in this file
