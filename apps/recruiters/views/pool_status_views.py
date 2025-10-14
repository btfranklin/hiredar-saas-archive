"""Views that expose progress information for candidate-pool creation tasks."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from apps.candidates.models import CandidatePool


class CandidatePoolStatusView(LoginRequiredMixin, TemplateView):
    """Return the *inner* HTML for a candidate-pool card.

    The view is designed exclusively for HTMX polling. It renders the same
    partial that the dashboard uses for the initial page load, ensuring the
    markup stays consistent regardless of whether it was served via full page
    render or an asynchronous fragment request.
    """

    template_name = "recruiters/components/pool_card_body.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        pool_id = self.kwargs["pool_id"]
        pool = get_object_or_404(
            CandidatePool, pk=pool_id, recruiter=self.request.user  # type: ignore[arg-type]
        )
        context["pool"] = pool
        return context


class CandidatePoolDetailStatusView(LoginRequiredMixin, TemplateView):
    """Return the inner HTML for a candidate-pool detail view (summary + rows) for HTMX polling."""

    template_name = "recruiters/components/candidate_pool_detail_body.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        pool_id = self.kwargs["pool_id"]
        pool = get_object_or_404(
            CandidatePool, pk=pool_id, recruiter=self.request.user  # type: ignore[arg-type]
        )
        context["pool"] = pool
        return context
