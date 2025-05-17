"""
PDF text extraction utilities.

This module contains functions for extracting text content from resume PDFs.
"""

# Suppress noisy CropBox/MediaBox warnings from pdfminer that clutter logs
import logging
import os

import pdfplumber

# Ensure pdfminer logger stays quiet unless error
for _name in (
    "pdfminer",
    "pdfminer.pdfpage",
):
    logging.getLogger(_name).setLevel(logging.ERROR)

# Setup logging
logger = logging.getLogger(__name__)

# NEW: Supported resume extensions (will be kept in sync with validators)
SUPPORTED_RESUME_EXTENSIONS: set[str] = {
    ".pdf",
    ".doc",
    ".docx",
    ".rtf",
    ".odt",
    ".txt",
}

try:
    # `unstructured` is an optional heavy dependency – import lazily
    from unstructured.documents.elements import Element  # type: ignore
    from unstructured.partition.auto import partition  # type: ignore

    _UNSTRUCTURED_AVAILABLE = True
    _Element = Element  # alias to satisfy type checkers without runtime dependency when unavailable
except Exception:  # pragma: no cover – import may fail in minimal envs
    _UNSTRUCTURED_AVAILABLE = False
    _Element = object  # type: ignore


def extract_text_from_pdf(file_path: str) -> str | None:
    """
    Extract text content from a PDF file.

    Args:
        file_path: Path to the PDF file

    Returns:
        The extracted text content or None if extraction fails
    """
    try:
        # Ensure file exists
        if not os.path.exists(file_path):
            logger.error(
                "Error extracting text from PDF: File does not exist at %s", file_path
            )
            return None

        # Ensure file is readable
        if not os.access(file_path, os.R_OK):
            logger.error(
                "Error extracting text from PDF: File is not readable at %s", file_path
            )
            return None

        # Log file size for debugging
        file_size = os.path.getsize(file_path) / 1024  # Size in KB
        logger.info("Extracting text from PDF: %s (%.1f KB)", file_path, file_size)

        text_content = []

        with pdfplumber.open(file_path) as pdf:
            # Log number of pages
            logger.info("PDF has %d pages", len(pdf.pages))

            # Extract text from each page
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    text_content.append(text)
                    logger.debug("Extracted %d characters from page %d", len(text), i)
                else:
                    logger.warning("No text extracted from page %d", i)

        # Join all the text with newlines
        result = "\n".join(text_content)
        logger.info(
            "Extracted %d characters from %d pages", len(result), len(pdf.pages)
        )
        return result

    except Exception as e:
        logger.error("Error extracting text from PDF: %s", str(e))
        return None


# ---------------------------------------------------------------------------
# Generic text extraction wrapper
# ---------------------------------------------------------------------------


def extract_text(file_path: str) -> str | None:
    """Extract **plain text** from *file_path* using *unstructured*.

    Falls back to :pyfunc:`extract_text_from_pdf` for PDFs if the library is
    unavailable or raises.  Returns *None* on failure.
    """

    # Fast path – specific PDF extractor is battle-tested and may be faster.
    if file_path.lower().endswith(".pdf") and not _UNSTRUCTURED_AVAILABLE:
        return extract_text_from_pdf(file_path)

    # Attempt via *unstructured* if present
    if _UNSTRUCTURED_AVAILABLE:
        try:
            elements = partition(filename=file_path)  # type: ignore[assignment]
            # Most Element subclasses have ``.text`` – filter out tables with
            # no textual content for now.
            text_blocks = [
                el.text.strip() for el in elements if getattr(el, "text", None)
            ]
            joined = "\n".join(text_blocks).strip()
            if joined:
                return joined
        except Exception as exc:  # noqa: BLE001 – broad catch for robustness
            logger.error(
                "Error extracting text with unstructured: %s", exc, exc_info=True
            )
            # PDF fallback – sometimes *unstructured* fails on heavily-scanned PDFs
            if file_path.lower().endswith(".pdf"):
                return extract_text_from_pdf(file_path)
            return None

    # Last-resort – if unstructured missing *and* not a PDF
    logger.error("No extractor available for file type: %s", file_path)
    return None


__all__ = [
    "extract_text_from_pdf",
    "extract_text",
    "SUPPORTED_RESUME_EXTENSIONS",
]
