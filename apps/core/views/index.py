"""
Core application views.

This module contains views for the core application,
including the home page and any other central site functionality.
"""

from typing import cast

from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import redirect
from django.views.generic import TemplateView

from apps.authentication.types import AuthenticatedUser

# Create your views here.


class HomeView(TemplateView):
    """View for the home page."""

    template_name = "core/home.html"

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponseBase:
        if request.user.is_authenticated:
            user = cast(AuthenticatedUser, request.user)
            if user.user_type == "recruiter":
                return redirect("recruiters:dashboard")
            elif user.user_type == "job_seeker":
                return redirect("job_seekers:dashboard")
            elif user.user_type == "admin":
                return redirect("/admin/")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["hide_brochure_nav"] = True
        return context


class RecruiterHomeView(TemplateView):
    """Marketing landing page for recruiters."""

    template_name = "core/recruiters/home.html"


class JobSeekerHomeView(TemplateView):
    """Marketing landing page for job seekers."""

    template_name = "core/job_seekers/home.html"
