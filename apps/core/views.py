"""
Core application views.

This module contains views for the core application,
including the home page and any other central site functionality.
"""

from django.views.generic import TemplateView

# Create your views here.


class HomeView(TemplateView):
    """View for the home page."""

    template_name = "core/home.html"
