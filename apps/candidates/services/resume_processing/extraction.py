"""
Resume text extraction helpers.

Provides utilities for extracting text from PDF and other document formats while
isolating heavy native dependencies inside standalone Python subprocesses. This
keeps Celery workers stable even when third-party libraries use unsafe globals.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys

from apps.candidates.extraction_worker.core import extract_pdf_text

# Supported resume extensions (keep in sync with validators)
SUPPORTED_RESUME_EXTENSIONS: set[str] = {
    ".pdf",
    ".doc",
    ".docx",
    ".rtf",
    ".odt",
    ".txt",
}

logger = logging.getLogger(__name__)
EXTRACTION_TIMEOUT_SECONDS: int = int(
    os.getenv("RESUME_EXTRACTION_TIMEOUT_SECONDS", "90")
)
SUBPROCESS_MODULE = "apps.candidates.extraction_worker.worker"


def _run_subprocess_extractor(
    mode: str,
    file_path: str,
    timeout: int | float | None = None,
) -> tuple[str | None, str | None]:
    """
    Execute the extractor subprocess and return (text, error).
    """
    timeout_seconds = timeout or EXTRACTION_TIMEOUT_SECONDS
    python_executable = sys.executable or "python"

    cmd = [
        python_executable,
        "-m",
        SUBPROCESS_MODULE,
        mode,
        file_path,
    ]

    try:
        completed = subprocess.run(  # noqa: S603 - trusted command
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        message = f"Extractor subprocess timed out after {timeout_seconds}s"
        logger.error("%s for %s (mode=%s)", message, file_path, mode)
        return None, message
    except Exception as exc:  # pragma: no cover - defensive
        message = f"Failed to start extractor subprocess: {exc}"
        logger.error(message, exc_info=True)
        return None, message

    raw_output = (completed.stdout or "").strip()
    if not raw_output:
        raw_output = (completed.stderr or "").strip()

    try:
        payload = json.loads(raw_output or "{}")
    except json.JSONDecodeError:
        message = (
            f"Extractor subprocess returned invalid JSON (code={completed.returncode})"
        )
        logger.error("%s: %s", message, raw_output)
        return None, message

    status = payload.get("status")
    text = payload.get("text")
    error = payload.get("error")

    if status == "success" and isinstance(text, str) and text.strip():
        return text.strip(), None

    if completed.returncode != 0:
        logger.debug(
            "Extractor subprocess exited with code %s for %s (mode=%s): %s",
            completed.returncode,
            file_path,
            mode,
            error or raw_output,
        )

    if not error:
        error = f"Extractor returned status '{status}'"
    return None, error


def _extract_text_with_unstructured(file_path: str) -> str | None:
    """
    Extract text for non-PDF resumes using the unstructured subprocess helper.
    """
    text, error = _run_subprocess_extractor("unstructured", file_path)
    if text:
        return text

    logger.debug("Unstructured extractor returned no text for %s: %s", file_path, error)
    if file_path.lower().endswith(".pdf"):
        logger.debug("Falling back to PDF extractor for %s", file_path)
        return extract_text_from_pdf(file_path)
    return None


def extract_text_from_pdf(file_path: str) -> str | None:
    """
    Extract text content from a PDF file using an isolated subprocess.
    """
    text, error = _run_subprocess_extractor("pdf", file_path)
    if text:
        return text

    logger.error("PDF extractor failed for %s: %s", file_path, error)
    # As a last resort, attempt inline extraction to avoid losing data entirely.
    inline_text, inline_error = extract_pdf_text(file_path)
    if inline_text:
        return inline_text
    if inline_error:
        logger.error(
            "Inline PDF extraction also failed for %s: %s", file_path, inline_error
        )
    return None


def extract_text(file_path: str) -> str | None:
    """
    Extract plain text from a supported resume file.

    Attempts to use a subprocess-backed extractor for non-PDF documents,
    falling back to PDF extraction when applicable.
    Returns None on failure.
    """
    normalized_path = file_path.lower()
    if normalized_path.endswith(".pdf"):
        return extract_text_from_pdf(file_path)

    if normalized_path.endswith(".txt"):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
                content = handle.read().strip()
                if content:
                    return content
        except Exception as exc:
            logger.error(
                "Error reading text file %s: %s", file_path, exc, exc_info=True
            )
            return None

    return _extract_text_with_unstructured(file_path)


__all__ = [
    "extract_text_from_pdf",
    "extract_text",
    "SUPPORTED_RESUME_EXTENSIONS",
]
