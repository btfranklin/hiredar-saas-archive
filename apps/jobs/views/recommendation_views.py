"""
Recommendation-related views for the jobs app.

This module contains views for handling role recommendations for job seekers,
helping them discover potential career paths based on their skills and experience.
"""

from typing import Any, cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import redirect
from django.views.generic import ListView

from apps.authentication.types import AuthenticatedUser
from apps.jobs.models import RoleRecommendation


class RoleRecommendationsView(LoginRequiredMixin, ListView):
    """
    View for listing role recommendations for a job seeker.

    This view displays role recommendations for job seekers based on their
    skills and experience. Only accessible to job seekers.

    Attributes:
        template_name: The template to render for role recommendations.
        context_object_name: The name of the context variable for the recommendations.
    """

    template_name = "jobs/role_recommendations.html"
    context_object_name = "recommendations"

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """
        Check if the user is a job seeker before processing the request.

        Args:
            request: The HTTP request.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponseBase: The response to the request.
        """
        user = cast(AuthenticatedUser, request.user)
        if not user.is_authenticated or user.user_type != "job_seeker":
            return redirect("core:home")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[RoleRecommendation]:
        """
        Get the role recommendations to display for the job seeker.

        Returns:
            QuerySet[RoleRecommendation]: A queryset of role recommendations for the job seeker.
        """
        user = cast(AuthenticatedUser, self.request.user)
        return RoleRecommendation.objects.filter(
            job_seeker=user.job_seeker_profile
        ).order_by("-created_at")
