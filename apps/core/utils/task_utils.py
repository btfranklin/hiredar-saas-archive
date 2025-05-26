"""
Utilities for idempotent task management.
"""

import hashlib
import logging
from typing import Any

from celery import current_app
from celery.result import AsyncResult
from django.core.cache import cache

logger = logging.getLogger(__name__)


class IdempotentTaskManager:
    """Manager for ensuring task idempotency and preventing overlapping runs."""

    @staticmethod
    def generate_deterministic_task_id(task_name: str, *args: Any) -> str:
        """
        Generate a deterministic task ID based on task name and arguments.

        This ensures that the same task with the same arguments will always
        get the same task ID, enabling idempotency.

        Args:
            task_name: Name of the task
            *args: Task arguments to include in the ID generation

        Returns:
            Deterministic task ID string
        """
        # Create a string representation of the task and its arguments
        task_signature = f"{task_name}:{':'.join(str(arg) for arg in args)}"

        # Generate a hash for a consistent, shorter ID
        task_hash = hashlib.sha256(task_signature.encode()).hexdigest()[:16]

        return f"{task_name}_{task_hash}"

    @staticmethod
    def is_task_running(task_id: str) -> bool:
        """
        Check if a task with the given ID is currently running.

        Args:
            task_id: The task ID to check

        Returns:
            True if the task is running, False otherwise
        """
        try:
            result = AsyncResult(task_id, app=current_app)
            return result.state in ["PENDING", "STARTED", "RETRY"]
        except Exception as e:
            logger.warning("Error checking task status for %s: %s", task_id, e)
            return False

    @staticmethod
    def mark_task_running(task_id: str, timeout: int = 3600) -> bool:
        """
        Mark a task as running using cache-based locking.

        This provides an additional layer of protection against overlapping
        tasks beyond Celery's built-in mechanisms.

        Args:
            task_id: The task ID to mark as running
            timeout: How long to hold the lock (seconds)

        Returns:
            True if the lock was acquired, False if already locked
        """
        cache_key = f"task_running:{task_id}"

        # Try to set the cache key atomically
        # This will only succeed if the key doesn't already exist
        return cache.add(cache_key, True, timeout=timeout)

    @staticmethod
    def unmark_task_running(task_id: str) -> None:
        """
        Remove the running marker for a task.

        Args:
            task_id: The task ID to unmark
        """
        cache_key = f"task_running:{task_id}"
        cache.delete(cache_key)

    @staticmethod
    def safe_task_execution(
        task_func: Any,
        task_name: str,
        *args: Any,
        timeout: int = 3600,
        **kwargs: Any,
    ) -> str | None:
        """
        Execute a task with idempotency protection.

        This method:
        1. Generates a deterministic task ID
        2. Checks if the task is already running
        3. Marks the task as running if not
        4. Executes the task with the deterministic ID

        Args:
            task_func: The Celery task function to execute
            task_name: Name of the task for ID generation
            *args: Arguments to pass to the task
            timeout: Lock timeout in seconds
            **kwargs: Keyword arguments to pass to the task

        Returns:
            Task ID if task was started, None if already running
        """
        # Generate deterministic task ID
        task_id = IdempotentTaskManager.generate_deterministic_task_id(task_name, *args)

        # Check if task is already running
        if IdempotentTaskManager.is_task_running(task_id):
            logger.info("Task %s is already running, skipping", task_id)
            return None

        # Try to acquire the running lock
        if not IdempotentTaskManager.mark_task_running(task_id, timeout):
            logger.info("Could not acquire lock for task %s, skipping", task_id)
            return None

        try:
            # Execute the task with the deterministic ID
            result = task_func.apply_async(
                args=args,
                kwargs=kwargs,
                task_id=task_id,
            )
            logger.info("Started idempotent task %s", task_id)
            return result.id

        except Exception as e:
            # If task execution fails, release the lock
            IdempotentTaskManager.unmark_task_running(task_id)
            logger.error("Failed to start task %s: %s", task_id, e)
            raise
