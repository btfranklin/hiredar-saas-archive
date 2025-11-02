"""
Django admin configuration for the core app.
"""

from django.contrib import admin
from django_celery_results.admin import TaskResultAdmin
from django_celery_results.models import TaskResult

from apps.core.models import PageViewCount


class CustomTaskResultAdmin(TaskResultAdmin):
    """
    Custom admin for TaskResult to improve display and functionality.
    """

    list_display = [
        "task_name_display",
        "task_app_display",
        "task_id_short",
        "status",
        "date_created",
        "date_done",
        "worker",
    ]

    list_filter = [
        "status",
        "date_created",
        "date_done",
        "worker",
    ]

    search_fields = [
        "task_name",
        "task_id",
        "periodic_task_name",
    ]

    readonly_fields = [
        "task_id",
        "task_name",
        "status",
        "date_created",
        "date_done",
        "result",
        "meta",
        "traceback",
        "worker",
        "task_args",
        "task_kwargs",
        "periodic_task_name",
    ]

    def task_name_display(self, obj):
        """
        Display only the final part of the task name (the actual task function name).

        For example: 'apps.matching.tasks.remove_candidate_embeddings'
        becomes 'remove_candidate_embeddings'
        """
        if not obj.task_name:
            return "-"

        # Split by dots and take the last part
        parts = obj.task_name.split(".")
        if parts:
            return parts[-1]
        return obj.task_name

    task_name_display.short_description = "Task Name"
    task_name_display.admin_order_field = "task_name"

    def task_app_display(self, obj):
        """
        Display the app name from the task name.

        For example: 'apps.matching.tasks.remove_candidate_embeddings'
        shows 'matching'
        """
        if not obj.task_name:
            return "-"

        # Split by dots and extract the app name (second part after 'apps')
        parts = obj.task_name.split(".")
        if len(parts) >= 2 and parts[0] == "apps":
            return parts[1]
        return "-"

    task_app_display.short_description = "Task App"
    task_app_display.admin_order_field = "task_name"

    def task_id_short(self, obj):
        """
        Display a shortened version of the task ID.

        Shows first 8 characters of UUID for reference while keeping it compact.
        """
        if not obj.task_id:
            return "-"

        # Show first 8 characters for reference
        return obj.task_id[:8] + "..." if len(obj.task_id) > 8 else obj.task_id

    task_id_short.short_description = "Task ID"
    task_id_short.admin_order_field = "task_id"


# Unregister the default admin and register our custom one
admin.site.unregister(TaskResult)
admin.site.register(TaskResult, CustomTaskResultAdmin)


@admin.register(PageViewCount)
class PageViewCountAdmin(admin.ModelAdmin):
    """
    Admin configuration for simple page view counts.
    """

    list_display = ["path", "view_count", "last_viewed_at", "updated_at"]
    search_fields = ["path"]
    ordering = ["-view_count", "path"]
