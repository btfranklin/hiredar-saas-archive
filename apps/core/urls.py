"""
Core URL configuration.

This module defines the URL routes for core application functionality,
including the home page and test endpoints.
"""

from django.http import HttpRequest, HttpResponse
from django.urls import path
from django.views.generic import RedirectView

from apps.core.views.index import HomeView
from apps.core.views.info import (
    AboutView,
    ContactView,
    HowItWorksView,
    PrivacyPolicyView,
    TermsOfServiceView,
)

app_name = "core"


def test_view(request: HttpRequest) -> HttpResponse:
    """
    Simple test view for verification.

    Args:
        request: The HTTP request object

    Returns:
        A simple HTTP response with text confirmation
    """
    return HttpResponse("Test view works!")


urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path(
        "how-it-works/",
        HowItWorksView.as_view(),
        name="how_it_works",
    ),
    path(
        "features/",
        RedirectView.as_view(pattern_name="core:how_it_works", permanent=True),
        name="features_redirect",
    ),
    path("about/", AboutView.as_view(), name="about"),
    path("contact/", ContactView.as_view(), name="contact"),
    path("privacy/", PrivacyPolicyView.as_view(), name="privacy"),
    path("terms/", TermsOfServiceView.as_view(), name="terms"),
    path("test/", test_view, name="test"),
]
