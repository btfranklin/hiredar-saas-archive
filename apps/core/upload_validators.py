"""Reusable validators for uploaded files.

The project currently accepts PDF resumes (and potentially other files) from
untrusted users.  These helpers provide defence‑in‑depth by validating:

* **extension** – only ``.pdf`` is allowed at the moment;
* **MIME type** – must be *application/pdf* (based on ``python‑magic`` if
  available, falling back to Django's ``content_type``);
* **size** – enforced via settings with a sensible default (10 MB).

Integrate them by adding to a ``FileField`` or via manual checks in upload
views::

    from apps.core.upload_validators import (
        validate_file_extension,
        validate_file_mime,
        validate_file_size,
    )

    resume = models.FileField(validators=[
        validate_file_extension,
        validate_file_mime,
        validate_file_size,
    ])
"""

from __future__ import annotations

import logging
import mimetypes
import os
from typing import Callable

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _get_mime(
    path: str, fallback: str | None = None
) -> str | None:  # noqa: D401 – helper
    """Return best‑guess MIME type for *path*.

    Tries *python‑magic* first (if installed) because that inspects the file
    header.  Falls back to ``mimetypes.guess_type`` which relies on the file
    name.
    """

    try:
        import magic  # python‑magic (optional runtime dependency)

        return magic.from_file(path, mime=True)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 – library may be missing or fail
        guessed, _ = mimetypes.guess_type(path)
        return guessed or fallback


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_file_extension(file_obj) -> None:  # noqa: D401 – Django validator
    """Ensure the file has a *.pdf* extension."""

    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext != ".pdf":
        raise ValidationError(_("Unsupported file extension – only PDF allowed."))


def validate_file_mime(file_obj) -> None:  # noqa: D401 – Django validator
    """Ensure the file's MIME type is *application/pdf*."""

    # ``content_type`` is provided by ``UploadedFile`` in request lifecycle
    mime = getattr(file_obj, "content_type", None)

    if not mime and hasattr(file_obj, "temporary_file_path"):
        mime = _get_mime(file_obj.temporary_file_path())

    if mime != "application/pdf":
        raise ValidationError(_("Invalid MIME type – only PDF documents are accepted."))


def validate_file_size(file_obj) -> None:  # noqa: D401 – Django validator
    """Reject files larger than *settings.MAX_UPLOAD_SIZE* (default 10 MB)."""

    max_bytes = getattr(settings, "MAX_UPLOAD_SIZE", 10 * 1024 * 1024)
    if file_obj.size > max_bytes:
        raise ValidationError(
            _(f"File too large – maximum size is {max_bytes / (1024*1024):.0f} MB.")
        )


# Bundle as convenience list
DEFAULT_PDF_VALIDATORS: list[Callable] = [
    validate_file_extension,
    validate_file_mime,
    validate_file_size,
]

# ---------------------------------------------------------------------------
# ZIP upload validators (for bulk resume archives)
# ---------------------------------------------------------------------------


def validate_zip_file_type(file_obj) -> None:  # noqa: D401 – Django validator
    """Ensure the file is a ZIP archive (checks extension and MIME)."""

    # Check extension
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext != ".zip":
        raise ValidationError(_("Unsupported file type – only ZIP archives allowed."))

    # If possible, inspect file header for correct MIME
    if hasattr(file_obj, "temporary_file_path"):
        mime = _get_mime(file_obj.temporary_file_path())
        # Accept common zip mime strings
        accepted_mimes = {"application/zip", "application/x-zip-compressed"}
        if mime not in accepted_mimes:
            raise ValidationError(
                _("Unsupported file type – only ZIP archives allowed.")
            )


def validate_zip_size(file_obj) -> None:  # noqa: D401 – Django validator
    """Reject ZIPs larger than *settings.MAX_ZIP_UPLOAD_SIZE* (default 100 MB)."""

    max_bytes = getattr(settings, "MAX_ZIP_UPLOAD_SIZE", 100 * 1024 * 1024)
    if file_obj.size > max_bytes:
        raise ValidationError(
            _(f"File too large – maximum ZIP size is {max_bytes / (1024*1024):.0f} MB.")
        )


DEFAULT_ZIP_VALIDATORS: list[Callable] = [
    validate_zip_file_type,
    validate_zip_size,
]
