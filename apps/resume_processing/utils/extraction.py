"""
PDF text extraction utilities.

This module contains functions for extracting text content from resume PDFs and other
supported resume formats, deferring heavy imports until needed to avoid forking issues.
"""

import logging
import os

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


def extract_text_from_pdf(file_path: str) -> str | None:
    """
    Extract text content from a PDF file using pdfplumber.

    Args:
        file_path: Path to the PDF file

    Returns:
        The extracted text content or None if extraction fails
    """
    try:
        import pdfplumber

        for _name in ("pdfminer", "pdfminer.pdfpage"):
            logging.getLogger(_name).setLevel(logging.ERROR)

        if not os.path.exists(file_path) or not os.access(file_path, os.R_OK):
            logger.error("Cannot extract text; file inaccessible: %s", file_path)
            return None

        file_size = os.path.getsize(file_path) / 1024
        logger.info("Extracting text from PDF: %s (%.1f KB)", file_path, file_size)
        text_content: list[str] = []

        with pdfplumber.open(file_path) as pdf:
            logger.info("PDF has %d pages", len(pdf.pages))
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    text_content.append(text)
                    logger.debug("Extracted %d characters from page %d", len(text), i)
                else:
                    logger.warning("No text extracted from page %d", i)

        result = "\n".join(text_content)
        logger.info("Extracted %d characters total", len(result))
        return result
    except Exception as exc:
        logger.error("Error extracting text from PDF: %s", exc, exc_info=True)
        return None


def extract_text(file_path: str) -> str | None:
    """
    Extract plain text from a supported resume file.

    Attempts to use the 'unstructured' library for non-PDFs if available,
    falling back to PDF extraction when applicable.
    Returns None on failure.
    """
    if file_path.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_path)

    try:
        from unstructured.partition.auto import partition  # type: ignore

        elements = partition(filename=file_path)  # type: ignore[assignment]
        text_blocks = [el.text.strip() for el in elements if getattr(el, "text", None)]
        joined = "\n".join(text_blocks).strip()
        if joined:
            return joined
    except Exception:
        logger.debug("Unstructured extractor unavailable or failed for: %s", file_path)
        if file_path.lower().endswith(".pdf"):
            return extract_text_from_pdf(file_path)

    logger.error("No extractor available for file type: %s", file_path)
    return None


__all__ = [
    "extract_text_from_pdf",
    "extract_text",
    "SUPPORTED_RESUME_EXTENSIONS",
]
