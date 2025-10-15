"""
Views for the recruiters app.

This module imports and exposes all views from the recruiters app's view modules,
making them available for import directly from apps.recruiters.views.
"""

from apps.recruiters.views.bulk_upload_views import (
    BulkResumeUploadView,
    CandidatePoolDeleteView,
    CandidatePoolDetailView,
    CandidatePoolListView,
    CandidatePoolProfileDetailView,
)
from apps.recruiters.views.dashboard_views import DashboardView, SettingsView
from apps.recruiters.views.job_opening_processing_views import (
    JobOpeningTaskStatusView,
    TextProcessJobOpeningView,
)
from apps.recruiters.views.job_opening_views import (
    JobOpeningCreateView,
    JobOpeningDeleteView,
    JobOpeningDetailView,
    JobOpeningEditView,
    JobOpeningListView,
    JobOpeningStatusChangeView,
)

# For backwards compatibility, expose all views at the module level
__all__ = [
    "DashboardView",
    "SettingsView",
    "JobOpeningCreateView",
    "JobOpeningListView",
    "JobOpeningDetailView",
    "JobOpeningEditView",
    "JobOpeningDeleteView",
    "JobOpeningStatusChangeView",
    "TextProcessJobOpeningView",
    "JobOpeningTaskStatusView",
    "BulkResumeUploadView",
    "CandidatePoolListView",
    "CandidatePoolDetailView",
    "CandidatePoolDeleteView",
    "CandidatePoolProfileDetailView",
]
