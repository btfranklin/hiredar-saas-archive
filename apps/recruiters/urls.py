"""URL patterns for the recruiters app."""

from django.urls import path
from django.urls.resolvers import URLPattern

from apps.recruiters.views import (
    BulkResumeUploadView,
    DashboardView,
    JobOpeningCreateView,
    JobOpeningDeleteView,
    JobOpeningDetailView,
    JobOpeningEditView,
    JobOpeningListView,
    JobOpeningTaskStatusView,
    ResumePoolDetailView,
    ResumePoolListView,
    SettingsView,
    TextProcessJobOpeningView,
)
from apps.recruiters.views.bulk_upload_views import ResumePoolDeleteView
from apps.recruiters.views.credit_views import (
    CheckoutSuccessView,
    CreditsView,
    create_checkout_session,
)

app_name = "recruiters"

urlpatterns: list[URLPattern] = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("settings/", SettingsView.as_view(), name="settings"),
    # Job Opening routes
    path("job-openings/", JobOpeningListView.as_view(), name="job_openings_list"),
    path(
        "job-openings/create/",
        JobOpeningCreateView.as_view(),
        name="job_openings_create",
    ),
    path(
        "job-openings/process/",
        TextProcessJobOpeningView.as_view(),
        name="job_openings_text_process",
    ),
    path(
        "job-openings/process/<str:task_id>/",
        JobOpeningTaskStatusView.as_view(),
        name="job_openings_process_status",
    ),
    path(
        "job-openings/<int:pk>/",
        JobOpeningDetailView.as_view(),
        name="job_openings_detail",
    ),
    path(
        "job-openings/<int:pk>/edit/",
        JobOpeningEditView.as_view(),
        name="job_openings_edit",
    ),
    path(
        "job-openings/<int:pk>/delete/",
        JobOpeningDeleteView.as_view(),
        name="job_openings_delete",
    ),
    # Bulk resume upload
    path("bulk-upload/", BulkResumeUploadView.as_view(), name="bulk_upload_create"),
    # Full resume pool list page
    path(
        "resume-pools/",
        ResumePoolListView.as_view(),
        name="resume_pool_list",
    ),
    # Detail view for processed resume pool
    path(
        "resume-pools/<int:pk>/",
        ResumePoolDetailView.as_view(),
        name="resume_pool_detail",
    ),
    # Delete view for processed resume pool
    path(
        "resume-pools/<int:pk>/delete/",
        ResumePoolDeleteView.as_view(),
        name="resume_pool_delete",
    ),
    # Credits / subscription routes
    path("credits/", CreditsView.as_view(), name="credits"),
    path(
        "credits/create/<int:credits_amount>/",
        create_checkout_session,
        name="create_checkout",
    ),
    path("credits/success/", CheckoutSuccessView.as_view(), name="checkout_success"),
]
