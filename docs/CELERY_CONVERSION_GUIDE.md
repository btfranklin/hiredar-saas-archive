# Celery Conversion Guide: From Hooks to Pure Celery Patterns

This guide provides a comprehensive approach for converting legacy hook-based task patterns to pure Celery implementations. It consolidates lessons learned from converting both the matching and recruiter apps.

## Overview

### What We're Converting FROM:
- **Hook-based task chaining**: Tasks that use `hook=function_name` parameters
- **Manual task chaining**: Using `async_task()` calls within task functions
- **Legacy Q-style patterns**: Holdovers from Django Q migration

### What We're Converting TO:
- **Native Celery chains**: Using `chain()`, `group()`, `chord()` primitives
- **Proper task signatures**: Using `.si()` and `.s()` methods
- **Structured return values**: Consistent dictionary returns for chaining
- **Standard Celery patterns**: Leveraging Celery's built-in capabilities

## Core Concepts

### 1. Task Signatures

**Immutable Signatures (`.si()`)**
- Use for the first task in a chain
- Receives only explicit arguments, ignores previous task results
- Example: `create_embeddings.si(job_id)`

**Regular Signatures (`.s()`)**  
- Use for subsequent tasks in a chain
- Receives the result from the previous task as first argument
- Example: `create_matches.s()`

### 2. Structured Return Values

All tasks must return dictionaries with consistent structure:

```python
{
    "status": "success|error|skipped",
    "message": "Optional description", 
    "data_field": "Task-specific data for next task",
    # ... other fields as needed
}
```

### 3. Semantic Task Naming (CRITICAL)

**Always use semantic task names instead of UUIDs.** This is essential for:
- **Debugging**: Understand what tasks are doing from logs
- **Monitoring**: Identify problematic task patterns
- **Operations**: Track task performance over time

```python
# ❌ BAD: UUID task names (default behavior)
async_task(my_task, arg1, arg2)  # Results in random UUID like "a4b8c2e3-..."

# ✅ GOOD: Semantic task names
async_task(my_task, arg1, arg2, task_name=f"process_resume_{user_id}")
chain(...).apply_async(task_id=f"embed_and_match_job_{job_id}")
```

### 4. Chain Patterns

**Sequential Processing:**
```python
from celery import chain

task_chain = chain(
    first_task.si(arg1, arg2),
    second_task.s(),
    third_task.s()
)
result = task_chain.apply_async()
```

**Parallel Processing:**
```python
from celery import group

parallel_tasks = group(
    task_a.si(data_a),
    task_b.si(data_b),
    task_c.si(data_c)
)
result = parallel_tasks.apply_async()
```

**Map-Reduce Pattern:**
```python
from celery import chord

map_reduce = chord(
    group(process_item.si(item) for item in items),
    aggregate_results.s()
)
result = map_reduce.apply_async()
```

## Clean Conversion Strategy

**IMPORTANT: Do NOT implement backwards compatibility during conversion.** 

The goal is a clean, modern implementation using pure Celery patterns. Backwards compatibility:
- Increases complexity and technical debt
- Creates confusion about which patterns to use
- Slows down the migration process
- Maintains problematic legacy code paths

**Instead:**
- Convert all hook usage to chains in one go
- Update all calling code simultaneously  
- Remove legacy hook functions entirely
- Focus on clean, modern Celery patterns only
- Test thoroughly but don't maintain dual code paths

## Step-by-Step Conversion Process

### Step 1: Identify Hook Usage Patterns

Search for these patterns in your codebase:

```bash
grep -r "hook=" apps/
grep -r "async_task.*hook" apps/
grep -r "def.*hook" apps/
```

Common patterns to convert:
- `async_task(task_func, args, hook=cleanup_func)`
- `safe_async_task(task_func, args, hook=follow_up_func)`
- Hook functions that call other tasks

### Step 2: Convert Hook Functions to Proper Tasks

**Before (Hook Function):**
```python
def cleanup_function(task: Task) -> None:
    result_data = task.result or {}
    file_path = result_data.get("file_path")
    if file_path and os.path.exists(file_path):
        os.unlink(file_path)
```

**After (Proper Task):**
```python
@shared_task(name="app.module.cleanup_function")
def cleanup_function(result: dict[str, Any] | None = None) -> dict[str, Any]:
    if not result or not isinstance(result, dict):
        return {"status": "error", "message": "No result provided"}
        
    file_path = result.get("file_path")
    if not file_path:
        return {"status": "error", "message": "No file_path in result"}
        
    if os.path.exists(file_path):
        try:
            os.unlink(file_path)
            return {"status": "success", "message": f"Cleaned up {file_path}"}
        except Exception as exc:
            return {"status": "error", "message": f"Cleanup failed: {exc}"}
    else:
        return {"status": "skipped", "message": "File already cleaned up"}
```

### Step 3: Update Task Return Values

**Before (Inconsistent Returns):**
```python
def process_data(data_id: int) -> None:
    # ... processing ...
    async_task(cleanup_task, result_data, hook=final_cleanup)
```

**After (Structured Returns):**
```python
def process_data(data_id: int) -> dict[str, Any]:
    try:
        # ... processing ...
        return {
            "status": "success",
            "data_id": data_id,
            "file_path": processed_file_path,
            "items_processed": count
        }
    except Exception as exc:
        return {
            "status": "error", 
            "message": str(exc),
            "data_id": data_id
        }
```

### Step 4: Replace Hook Calls with Chains AND Add Semantic Names

**Before (Hook-based):**
```python
# In main task
async_task(
    process_resume_for_pool,
    file_path,
    pool_id,
    bulk_pk,
    hook=cleanup_temp_file,
    queue="default"
)  # ❌ No task_name = UUID generated
```

**After (Chain-based with semantic naming):**
```python
# In main task
from celery import chain

process_task = process_resume_for_pool.si(file_path, pool_id, bulk_pk)
cleanup_task = cleanup_temp_file.s()

task_chain = chain(process_task, cleanup_task)
async_result = task_chain.apply_async(
    task_id=f"process_and_cleanup_resume_{pool_id}_{bulk_pk}"  # ✅ Semantic name
)
```

**CRITICAL: Also update non-chained tasks:**
```python
# ❌ BEFORE: UUID will be generated
async_task(single_task, arg1, arg2)

# ✅ AFTER: Semantic name provided
async_task(
    single_task, 
    arg1, 
    arg2,
    task_name=f"single_task_{arg1}_{arg2}"
)
```

### Step 5: Update Signal Handlers

**Before (Manual Chaining):**
```python
@receiver(post_save, sender=JobOpening)
def handle_job_opening_save(sender, instance, created, **kwargs):
    if instance.status == "active":
        safe_async_task_once(
            "create_job_opening_embeddings",
            instance.id,
            task_name=f"embed_job_opening_{instance.id}",
        )
```

**After (Celery Chains):**
```python
@receiver(post_save, sender=JobOpening) 
def handle_job_opening_save(sender, instance, created, **kwargs):
    if instance.status == "active":
        chain(
            create_job_embeddings_task.si(instance.id),
            create_matches_task.s()
        ).apply_async(
            task_id=f"embed_and_match_job_{instance.id}"
        )
```

### Step 6: Handle Input Flexibility

Tasks in chains need to handle different input types:

```python
@shared_task
def flexible_task(result: dict[str, Any] | int | None = None) -> dict[str, Any]:
    # Handle different input types for chain compatibility
    if isinstance(result, dict):
        item_id = result.get("item_id")
        status = result.get("status", "unknown")
    elif isinstance(result, int):
        item_id = result
        status = "direct_call"
    elif result is None:
        return {"status": "error", "message": "No input provided"}
    else:
        return {"status": "error", "message": f"Unexpected input type: {type(result)}"}
    
    # ... task logic ...
    return {"status": "success", "item_id": item_id}
```

## Real-World Examples

### Example 1: Bulk File Processing (Recruiter App)

**Before:**
```python
# Hook-based approach
async_task(
    process_resume_for_pool,
    local_path,
    candidate_pool.pk, 
    bulk.pk,
    str(meta.pk),
    hook=cleanup_temp_resume_file,
    queue="default",
)

def cleanup_temp_resume_file(task: Task) -> None:
    result_data = task.result or {}
    file_path = result_data.get("file_path")
    # ... cleanup logic
```

**After:**
```python
# Chain-based approach
process_task = process_resume_for_pool.si(
    local_path,
    candidate_pool.pk,
    bulk.pk, 
    str(meta.pk),
)
cleanup_task = cleanup_temp_resume_file.s()

task_chain = chain(process_task, cleanup_task)
async_result = task_chain.apply_async(
    task_id=f"candidate_pool_process_{task_id}"
)

@shared_task
def cleanup_temp_resume_file(result: dict[str, Any] | None = None) -> dict[str, Any]:
    # ... proper task implementation with structured returns
```

### Example 2: Job Matching Pipeline (Matching App)

**Before:**
```python
def create_job_opening_embeddings(job_opening_id: int) -> None:
    # ... create embeddings ...
    async_task(create_candidate_matches, job.id)
```

**After:**
```python
def create_job_opening_embeddings(job_opening_id: int) -> dict[str, Any]:
    try:
        # ... create embeddings ...
        return {"status": "success", "job_opening_id": job.id}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

def create_candidate_matches(result: dict[str, Any] | int | None = None) -> dict[str, Any]:
    # Handle different input types
    if isinstance(result, dict):
        job_id = result.get("job_opening_id")
    elif isinstance(result, int):
        job_id = result
    # ... matching logic ...
    return {"status": "success", "matches_created": count}

# In signal handler
chain(
    create_job_embeddings_task.si(instance.id),
    create_matches_task.s()
).apply_async(task_id=f"embed_and_match_job_{instance.id}")
```

## Best Practices

### 1. Consistent Error Handling

```python
@shared_task
def robust_task(input_data: Any) -> dict[str, Any]:
    try:
        # Validate input
        if not input_data:
            return {"status": "error", "message": "No input provided"}
            
        # Task logic here
        result = process_data(input_data)
        
        return {
            "status": "success",
            "data": result,
            "processed_at": datetime.now().isoformat()
        }
        
    except SpecificException as exc:
        return {
            "status": "error", 
            "message": f"Specific error: {exc}",
            "error_type": "specific"
        }
    except Exception as exc:
        logger.exception("Unexpected error in robust_task")
        return {
            "status": "error",
            "message": f"Unexpected error: {exc}",
            "error_type": "unexpected"
        }
```

### 2. Semantic Task Naming (MANDATORY)

**Every task MUST have a semantic name.** Never rely on Celery's auto-generated UUIDs.

```python
# ✅ EXCELLENT: Include relevant IDs and context
task_name = f"process_resume_{profile_id}_{timestamp}"
task_name = f"embed_and_match_job_{job.id}"
task_name = f"cleanup_temp_file_{bulk.pk}_{resume.id}"
task_name = f"generate_talent_sheet_{profile.pk}"
task_name = f"remove_job_embeddings_{job.id}"

# ✅ GOOD: Basic semantic naming
task_name = f"process_user_data_{user.id}"
task_name = f"send_email_{recipient.id}"

# ❌ NEVER: Let Celery generate UUIDs
async_task(my_task, args)  # Results in "a4b8c2e3-f1d2-..."
chain(...).apply_async()   # Results in random UUID

# ❌ AVOID: Generic or meaningless names
task_name = "task_123"
task_name = "background_job"
```

**Implementation patterns:**
```python
# For single tasks
async_task(
    process_data,
    data_id,
    task_name=f"process_data_{data_id}"
)

# For chains
chain(first_task.si(id), second_task.s()).apply_async(
    task_id=f"complete_workflow_{id}"
)

# With timestamps for uniqueness
import time
timestamp = int(time.time())
task_name = f"bulk_import_{batch_id}_{timestamp}"
```

### 3. Progress Tracking Integration

```python
@shared_task
def tracked_task(item_id: int, meta_pk: str | None = None) -> dict[str, Any]:
    # Update TaskMeta at key milestones
    meta = None
    if meta_pk:
        try:
            meta = TaskMeta.objects.get(pk=meta_pk)
            meta.state = TaskMeta.State.RUNNING
            meta.save(update_fields=["state"])
        except TaskMeta.DoesNotExist:
            pass
    
    try:
        # ... task work ...
        
        if meta:
            meta.state = TaskMeta.State.SUCCESS
            meta.progress = 100
            meta.save(update_fields=["state", "progress"])
            
        return {"status": "success", "item_id": item_id}
        
    except Exception as exc:
        if meta:
            meta.state = TaskMeta.State.FAILURE
            meta.save(update_fields=["state"])
        return {"status": "error", "message": str(exc)}
```

### 4. Type Safety

```python
from typing import Any, Union

# Use type hints for better development experience
@shared_task
def typed_task(
    input_data: Union[dict[str, Any], int, None] = None
) -> dict[str, Any]:
    # Implementation with type checking
    pass
```

## Testing Patterns

### Individual Task Testing

```python
def test_individual_task():
    result = my_task(test_input)
    assert result["status"] == "success"
    assert "expected_field" in result
```

### Chain Testing  

```python
def test_task_chain():
    # Test with apply() for synchronous execution in tests
    task_chain = chain(
        first_task.si(test_input),
        second_task.s()
    )
    result = task_chain.apply()
    
    # Verify final result
    assert result.result["status"] == "success"
    
    # Verify intermediate results if needed
    assert len(result.parent.result) > 0
```

### Input Type Testing

```python
def test_input_types():
    # Test different input types for chain compatibility
    
    # Direct integer input
    result1 = flexible_task(123)
    assert result1["status"] == "success"
    
    # Dictionary input from previous task
    result2 = flexible_task({"item_id": 123, "extra": "data"})
    assert result2["status"] == "success"
    
    # Chain input
    chain_result = chain(
        first_task.si(123),
        flexible_task.s()
    ).apply()
    assert chain_result.result["status"] == "success"
```

## Common Pitfalls and Solutions

### 1. Mypy/Type Checker Warnings

**Problem:** Mypy doesn't recognize `.si()` and `.s()` methods

**Solution:** Add type ignore comments
```python
process_task = process_resume_for_pool.si(args)  # type: ignore[misc]
cleanup_task = cleanup_temp_resume_file.s()     # type: ignore[misc]
```

### 2. Missing Return Values

**Problem:** Tasks that don't return data break chains

**Solution:** Always return structured dictionaries
```python
# Bad
def task_without_return(data):
    process(data)
    # No return statement

# Good  
def task_with_return(data):
    try:
        process(data)
        return {"status": "success", "data": processed_data}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
```

### 3. Hook Function Removal

**Problem:** Removing hook functions breaks existing tasks

**Solution:** Convert all hook usage to chains simultaneously and remove hook functions
```python
# ❌ DON'T keep deprecated functions
# def deprecated_hook_function(task: Task) -> None:
#     logger.warning("Hook function deprecated, use Celery chains instead")

# ✅ DO convert to proper task and update all callers
@shared_task
def proper_celery_task(result: dict[str, Any] | None = None) -> dict[str, Any]:
    # Clean implementation without legacy support
    return {"status": "success", "data": processed_data}
```

### 4. Import Cycles

**Problem:** Circular imports when converting to proper tasks

**Solution:** Use deferred imports or reorganize modules
```python
@shared_task
def task_with_deferred_import(data):
    # Import inside function to avoid cycles
    from apps.other.tasks import dependent_task
    # ... task logic
```

## Verification Checklist

After conversion, verify:

- [ ] All hook function calls removed
- [ ] All tasks return structured dictionaries  
- [ ] Chain signatures use `.si()` and `.s()` correctly
- [ ] Tasks handle different input types gracefully
- [ ] Error handling returns consistent error structures
- [ ] **ALL TASKS HAVE SEMANTIC NAMES (NO UUIDs)**
- [ ] Task names include relevant IDs and context
- [ ] Tests cover both individual tasks and chains
- [ ] No remaining `async_task(..., hook=...)` patterns
- [ ] Import statements cleaned up
- [ ] Celery admin shows readable task names
- [ ] Monitoring dashboards display meaningful task identifiers

## Migration Strategy

### Phase 1: Preparation
1. Identify all hook usage patterns
2. Plan the conversion order (dependencies first)
3. Create tests for existing functionality

### Phase 2: Convert Tasks
1. Convert hook functions to proper tasks
2. Update task return values
3. Add input type flexibility

### Phase 3: Convert Callers  
1. Replace hook calls with chains
2. Update signal handlers
3. Update views and other entry points

### Phase 4: Cleanup
1. Remove unused hook functions
2. Clean up imports
3. Update documentation

### Phase 5: Verification
1. Run full test suite
2. Test in staging environment
3. Monitor task execution in production
4. Verify monitoring tools show chains correctly

This systematic approach ensures a smooth transition from legacy patterns to modern Celery implementations while maintaining system reliability and developer productivity. 