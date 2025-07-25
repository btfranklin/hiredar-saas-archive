"""
URL configuration for hiredar project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Authentication (django-allauth)
    path("accounts/", include("allauth.urls")),
    # App URLs
    path("auth/", include("apps.authentication.urls", namespace="authentication")),
    path("matching/", include("apps.matching.urls", namespace="matching")),
    path("messaging/", include("apps.messaging.urls", namespace="messaging")),
    path("job-seekers/", include("apps.job_seekers.urls", namespace="job_seekers")),
    path("recruiters/", include("apps.recruiters.urls", namespace="recruiters")),
    path("reports/", include("apps.reports.urls", namespace="reports")),
    # Home page and core functionality
    path("", include("apps.core.urls", namespace="core")),
    # Icon redirects (handle browsers that automatically request these files at the root)
    path(
        "favicon.ico",
        RedirectView.as_view(
            url=f"{settings.STATIC_URL.rstrip('/')}/icons/favicon.ico", permanent=True
        ),
    ),
    path(
        "apple-touch-icon.png",
        RedirectView.as_view(
            url=f"{settings.STATIC_URL.rstrip('/')}/icons/apple-touch-icon.png",
            permanent=True,
        ),
    ),
    path(
        "apple-touch-icon-precomposed.png",
        RedirectView.as_view(
            url=f"{settings.STATIC_URL.rstrip('/')}/icons/apple-touch-icon.png",
            permanent=True,
        ),
    ),
    path(
        "sitemap.xml",
        RedirectView.as_view(
            url=f"{settings.STATIC_URL.rstrip('/')}/sitemap.xml",
            permanent=True,
        ),
    ),
    # Well-known plaintext files
    path(
        "robots.txt",
        RedirectView.as_view(
            url=f"{settings.STATIC_URL.rstrip('/')}/robots.txt",
            permanent=True,
        ),
    ),
    path(
        "llms.txt",
        RedirectView.as_view(
            url=f"{settings.STATIC_URL.rstrip('/')}/llms.txt",
            permanent=True,
        ),
    ),
]

# Serve media files in development
if settings.DEBUG:
    # Standard Django approach for media files
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Standard Django approach for static files
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
