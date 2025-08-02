"""Healthcheck endpoint for load balancer and uptime monitoring."""

from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_GET


@require_GET
def healthcheck(request: HttpRequest) -> HttpResponse:
    """Return a simple 200 OK response for health checks.

    Args:
        request: The incoming HTTP request.

    Returns:
        HttpResponse: Plain text "ok" with HTTP 200 status.
    """
    return HttpResponse("ok", status=200, content_type="text/plain")
