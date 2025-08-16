import logging

from django.core.exceptions import DisallowedHost


class IgnoreDisallowedHostFilter(logging.Filter):
    """Strip DisallowedHost tracebacks and downlevel severity.

    Keeps the log line but removes exc_info to avoid stack traces and
    converts ERROR to WARNING for this specific, expected condition.
    """

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        exc_info = record.exc_info
        if exc_info:
            _, exc_value, _ = exc_info
            if isinstance(exc_value, DisallowedHost):
                record.exc_info = None
                record.exc_text = None
                if record.levelno > logging.WARNING:
                    record.levelno = logging.WARNING
                    record.levelname = logging.getLevelName(logging.WARNING)
        return True
