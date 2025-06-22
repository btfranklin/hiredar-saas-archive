"""URL patterns for the recruiters app."""

from django.urls import path
from django.urls.resolvers import URLPattern

from apps.core.views.index import RecruiterHomeView
from apps.recruiters.views import (
    BulkResumeUploadView,
    CandidatePoolDetailView,
    CandidatePoolListView,
    DashboardView,
    JobOpeningCreateView,
    JobOpeningDeleteView,
    JobOpeningDetailView,
    JobOpeningEditView,
    JobOpeningListView,
    JobOpeningStatusChangeView,
    JobOpeningTaskStatusView,
    SettingsView,
    TextProcessJobOpeningView,
)
from apps.recruiters.views.bulk_upload_views import (
    CandidatePoolDeleteView,
    CandidatePoolTalentSheetDetailView,
)
from apps.recruiters.views.credit_views import (
    CheckoutSuccessView,
    CreditsView,
    create_checkout_session,
)
from apps.recruiters.views.pool_status_views import (
    CandidatePoolDetailStatusView,
    CandidatePoolStatusView,
)

app_name = "recruiters"

urlpatterns: list[URLPattern] = [
    path("", RecruiterHomeView.as_view(), name="marketing_home"),
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
    # Job opening status change
    path(
        "job-openings/<int:pk>/status/<str:action>/",
        JobOpeningStatusChangeView.as_view(),
        name="job_openings_status_change",
    ),
    # Bulk resume upload
    path("bulk-upload/", BulkResumeUploadView.as_view(), name="bulk_upload_create"),
    # Full resume pool list page
    path(
        "candidate-pools/",
        CandidatePoolListView.as_view(),
        name="candidate_pool_list",
    ),
    # Detail view for processed resume pool
    path(
        "candidate-pools/<int:pk>/",
        CandidatePoolDetailView.as_view(),
        name="candidate_pool_detail",
    ),
    # Talent sheet detail for a candidate in a resume pool
    path(
        "candidate-pools/<int:pool_pk>/profiles/<int:pk>/talent-sheet/",
        CandidatePoolTalentSheetDetailView.as_view(),
        name="candidate_pool_profile_talent_sheet_detail",
    ),
    # Delete view for processed resume pool
    path(
        "candidate-pools/<int:pk>/delete/",
        CandidatePoolDeleteView.as_view(),
        name="candidate_pool_delete",
    ),
    # Credits / subscription routes
    path("credits/", CreditsView.as_view(), name="credits"),
    path(
        "credits/create/<int:credits_amount>/",
        create_checkout_session,
        name="create_checkout",
    ),
    path("credits/success/", CheckoutSuccessView.as_view(), name="checkout_success"),
    # Candidate pool status (HTMX polling)
    path(
        "candidate-pools/<int:pool_id>/status/",
        CandidatePoolStatusView.as_view(),
        name="candidate_pool_status",
    ),
    # Candidate pool detail status (HTMX polling)
    path(
        "candidate-pools/<int:pool_id>/detail-status/",
        CandidatePoolDetailStatusView.as_view(),
        name="candidate_pool_detail_status",
    ),
]
