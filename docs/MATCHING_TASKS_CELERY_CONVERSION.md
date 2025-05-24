# Matching Tasks Celery Conversion

This document describes the conversion of the matching app's tasks from legacy Q-style hooks to pure Celery patterns.

## Overview

The matching app tasks were previously converted from Django Q but retained some legacy patterns, particularly the use of `async_task()` for chaining tasks. This has been updated to use Celery's native chaining capabilities.

## Changes Made

### 1. Task Return Values

All tasks now return structured dictionaries instead of `None`, enabling proper chaining:

```python
# Before
def create_job_opening_embeddings(job_opening_id: int, **kwargs) -> None:
    # ... process embeddings ...
    async_task(create_candidate_matches, job.id)

# After  
def create_job_opening_embeddings(job_opening_id: int, **kwargs) -> dict[str, Any]:
    # ... process embeddings ...
    return {"status": "success", "job_opening_id": job.id}
```

### 2. Task Signatures

Tasks that are part of chains now accept the result from the previous task:

```python
# Before
def create_candidate_matches(job_id: int, **kwargs) -> None:
    # ...

# After
def create_candidate_matches(result: dict[str, Any] | int | None = None, **kwargs) -> dict[str, Any]:
    # Handle different input types
    if isinstance(result, dict):
        job_id = result.get("job_opening_id")
    elif isinstance(result, int):
        job_id = result
    # ...
```

### 3. Signal Handlers Using Celery Chains

The signal handlers now use Celery's `chain()` primitive instead of manual task chaining:

```python
# Before (using safe_async_task_once with hooks)
safe_async_task_once(
    "apps.matching.tasks.create_job_opening_embeddings",
    instance.id,
    task_name=f"embed_job_opening_{instance.id}",
)

# After (using Celery chain)
chain(
    create_job_embeddings_task.si(instance.id),
    create_matches_task.s()
).apply_async(
    task_id=f"embed_and_match_job_{instance.id}"
)
```

## Task Flow

### Job Opening Flow

1. When a JobOpening is saved with status="active":
   - `create_job_opening_embeddings` is called
   - On success, it automatically triggers `create_candidate_matches`

### Talent Sheet Flow

1. When a TalentSheet is published:
   - `create_talent_sheet_embeddings` is called
   - On success, it automatically triggers `match_talent_to_active_jobs`

## Key Concepts

### Immutable Signatures (.si())

The first task in a chain uses `.si()` (immutable signature) to ensure it receives only its explicit arguments and not the result from a previous task.

### Regular Signatures (.s())

Subsequent tasks use `.s()` to create a signature that will receive the result from the previous task as its first argument.

### Error Handling

Each task returns a structured result with a status field:
- `"success"` - Task completed successfully
- `"error"` - Task encountered an error
- `"skipped"` - Task was skipped due to business logic

## Benefits

1. **Native Celery Features**: Uses Celery's built-in chaining capabilities
2. **Better Observability**: Task chains are visible in Celery monitoring tools
3. **Improved Performance**: No overhead from custom hook runners or deduplication logic
4. **Type Safety**: Clear input/output contracts for each task
5. **Flexibility**: Tasks can be called individually or as part of chains
6. **Code Simplification**: Removed unused `safe_async_task_once` function

## Testing

Tasks can be tested individually by passing appropriate input:

```python
# Direct call with job ID
create_candidate_matches(123)

# Call with result dict (as in chain)
create_candidate_matches({"status": "success", "job_opening_id": 123})
```

## Migration Notes

- The `async_task` alias for `safe_async_task` is still used for non-chained tasks
- All tasks maintain backward compatibility and can be called with their original signatures
- The linter may show false positives for `.si()` and `.s()` methods due to type stub limitations
- `safe_async_task_once` has been completely removed as it was no longer used 