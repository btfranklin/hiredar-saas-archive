"""Reusable validators for uploaded files.

The project currently accepts PDF resumes (and potentially other files) from
untrusted users.  These helpers provide defense‑in‑depth by validating:

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
# Validators – generic resume support
# ---------------------------------------------------------------------------

# Keep the full list in sync with *unstructured* integration layer
from apps.resume_processing.services.extraction import SUPPORTED_RESUME_EXTENSIONS

_EXT_TO_ALLOWED_MIME: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    },
    ".doc": {"application/msword"},
    ".rtf": {"application/rtf", "text/rtf"},
    ".odt": {"application/vnd.oasis.opendocument.text"},
    ".txt": {"text/plain"},
}


def validate_resume_file_extension(file_obj) -> None:  # noqa: D401 – Django validator
    """Ensure the file has an allowed *resume* extension."""

    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in SUPPORTED_RESUME_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_RESUME_EXTENSIONS))
        raise ValidationError(_(f"Unsupported file extension – allowed: {allowed}"))


def validate_resume_file_mime(file_obj) -> None:  # noqa: D401 – Django validator
    """Ensure the file's MIME type roughly matches the extension."""

    ext = os.path.splitext(file_obj.name)[1].lower()

    # Skip strict MIME matching if we don't recognize the extension (handled above).
    allowed_mimes = _EXT_TO_ALLOWED_MIME.get(ext)
    if not allowed_mimes:
        return

    # ``content_type`` is set by Django's ``UploadedFile``; may be empty.
    mime = getattr(file_obj, "content_type", None)

    if not mime and hasattr(file_obj, "temporary_file_path"):
        mime = _get_mime(file_obj.temporary_file_path())

    if mime and mime not in allowed_mimes:
        raise ValidationError(_("Invalid MIME type for the uploaded document."))


def validate_file_size(file_obj) -> None:  # noqa: D401 – Django validator
    """Reject files larger than *settings.MAX_UPLOAD_SIZE* (default 10 MB)."""

    max_bytes = getattr(settings, "MAX_UPLOAD_SIZE", 10 * 1024 * 1024)
    if file_obj.size > max_bytes:
        raise ValidationError(
            _(f"File too large – maximum size is {max_bytes / (1024*1024):.0f} MB.")
        )


# Bundle as convenience list (public API)
DEFAULT_RESUME_VALIDATORS: list[Callable] = [
    validate_resume_file_extension,
    validate_resume_file_mime,
    validate_file_size,
]

# Backwards-compat alias – remove once all imports are migrated
DEFAULT_PDF_VALIDATORS = DEFAULT_RESUME_VALIDATORS  # type: ignore

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
