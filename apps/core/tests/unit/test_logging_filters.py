import logging
import sys

from django.core.exceptions import DisallowedHost

from apps.core.logging import IgnoreDisallowedHostFilter


def _make_record(level: int, exc: BaseException | None) -> logging.LogRecord:
    record = logging.LogRecord(
        name="django.request",
        level=level,
        pathname=__file__,
        lineno=10,
        msg="Invalid HTTP_HOST header",
        args=(),
        exc_info=None,
    )
    if exc is not None:
        try:
            raise exc
        except type(exc):  # type: ignore[misc]
            record.exc_info = sys.exc_info()
    return record


def test_filter_strips_exc_info_and_downlevels_for_disallowed_host():
    filter_ = IgnoreDisallowedHostFilter()
    record = _make_record(logging.ERROR, DisallowedHost("Invalid host"))

    allowed = filter_.filter(record)

    assert allowed is True
    assert record.exc_info is None
    assert record.levelno == logging.WARNING
    assert record.levelname == logging.getLevelName(logging.WARNING)


def test_filter_keeps_other_exceptions_untouched():
    filter_ = IgnoreDisallowedHostFilter()
    record = _make_record(logging.ERROR, ValueError("boom"))

    allowed = filter_.filter(record)

    assert allowed is True
    assert record.exc_info is not None
    assert record.levelno == logging.ERROR
