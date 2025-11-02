"""
Middleware for incrementing simple page view counters.
"""

from __future__ import annotations

import logging
from typing import Iterable, Tuple

from django.conf import settings
from django.db import IntegrityError
from django.db.models import F
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from apps.core.models import PageViewCount

logger = logging.getLogger(__name__)


class PageViewCountMiddleware:
    """
    Records GET requests for selected routes in the PageViewCount model.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._ignored_prefixes = self._build_ignored_prefixes()
        self._allowed_namespaces = tuple(
            getattr(
                settings,
                "PAGE_VIEW_COUNT_ALLOWED_NAMESPACES",
                ("core",),
            )
        )
        self._allowed_view_names = tuple(
            getattr(
                settings,
                "PAGE_VIEW_COUNT_ALLOWED_VIEW_NAMES",
                ("authentication:signup",),
            )
        )

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        if self._should_track(request, response):
            try:
                self._increment_counter(request.path)
            except Exception:  # pragma: no cover - safeguard against analytics failures
                logger.exception("Failed to record page view for path %s", request.path)

        return response

    def _should_track(self, request: HttpRequest, response: HttpResponse) -> bool:
        if request.method != "GET":
            return False

        if response.status_code >= 400:
            return False

        path = request.path or "/"
        for prefix in self._ignored_prefixes:
            if prefix and path.startswith(prefix):
                return False

        return self._is_allowed_route(request)

    def _build_ignored_prefixes(self) -> Tuple[str, ...]:
        prefixes: list[str] = []

        static_url = getattr(settings, "STATIC_URL", "")
        media_url = getattr(settings, "MEDIA_URL", "")
        admin_url = getattr(settings, "ADMIN_URL", "") or "/admin/"

        prefixes.extend(self._normalize_prefixes([static_url, media_url, admin_url]))
        custom = getattr(settings, "PAGE_VIEW_COUNT_IGNORE_PREFIXES", ())
        prefixes.extend(self._normalize_prefixes(custom))

        return tuple(prefixes)

    @staticmethod
    def _normalize_prefixes(prefixes: Iterable[str]) -> list[str]:
        normalized: list[str] = []
        for prefix in prefixes:
            if not prefix:
                continue
            if not prefix.startswith("/"):
                prefix = f"/{prefix}"
            normalized.append(prefix)
        return normalized

    def _is_allowed_route(self, request: HttpRequest) -> bool:
        resolver_match = getattr(request, "resolver_match", None)
        if resolver_match is None:
            return False

        view_name = resolver_match.view_name or ""
        if view_name in self._allowed_view_names:
            return True

        if not self._allowed_namespaces:
            return False

        namespaces = list(resolver_match.namespaces)
        if resolver_match.namespace:
            namespaces.append(resolver_match.namespace)

        for namespace in namespaces:
            if namespace and namespace in self._allowed_namespaces:
                return True

        return False

    @staticmethod
    def _increment_counter(path: str) -> None:
        now = timezone.now()

        updated = PageViewCount.objects.filter(path=path).update(
            view_count=F("view_count") + 1,
            last_viewed_at=now,
        )

        if updated:
            return

        try:
            PageViewCount.objects.create(
                path=path,
                view_count=1,
                last_viewed_at=now,
            )
        except IntegrityError:
            PageViewCount.objects.filter(path=path).update(
                view_count=F("view_count") + 1,
                last_viewed_at=now,
            )
