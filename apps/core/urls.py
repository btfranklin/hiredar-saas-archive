"""
Core URL configuration.

This module defines the URL routes for core application functionality,
including the home page and test endpoints.
"""

from django.http import HttpRequest, HttpResponse
from django.urls import path

from apps.core.views.index import HomeView
from apps.core.views.info import (
    AboutView,
    ContactView,
    JobSeekerFeaturesView,
    ManifestoView,
    PrivacyPolicyView,
    RecruiterFeaturesView,
    RecruiterPricingSignupView,
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
        "features/recruiters/",
        RecruiterFeaturesView.as_view(),
        name="features_recruiters",
    ),
    path(
        "features/job-seekers/",
        JobSeekerFeaturesView.as_view(),
        name="features_job_seekers",
    ),
    path("pricing/", RecruiterPricingSignupView.as_view(), name="pricing"),
    path("about/", AboutView.as_view(), name="about"),
    path("contact/", ContactView.as_view(), name="contact"),
    path("privacy/", PrivacyPolicyView.as_view(), name="privacy"),
    path("manifesto/", ManifestoView.as_view(), name="manifesto"),
    path("terms/", TermsOfServiceView.as_view(), name="terms"),
    path("test/", test_view, name="test"),
]
