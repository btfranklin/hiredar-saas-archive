"""Shared extraction helpers for the subprocess worker."""

from __future__ import annotations

import logging
import os
from typing import Tuple

logger = logging.getLogger(__name__)


def extract_pdf_text(file_path: str) -> Tuple[str | None, str | None]:
    """Extract text content from a PDF file using pdfplumber."""

    try:
        import pdfplumber

        for _name in ("pdfminer", "pdfminer.pdfpage"):
            logging.getLogger(_name).setLevel(logging.ERROR)

        if not os.path.exists(file_path) or not os.access(file_path, os.R_OK):
            error = f"Cannot extract text; file inaccessible: {file_path}"
            logger.error(error)
            return None, error

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
        if not result.strip():
            error = "PDF extraction produced no text"
            logger.warning("%s: %s", error, file_path)
            return None, error

        logger.info("Extracted %d characters total", len(result))
        return result, None
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Error extracting text from PDF: %s", exc, exc_info=True)
        return None, f"{exc.__class__.__name__}: {exc}"


def extract_unstructured_text(file_path: str) -> Tuple[str | None, str | None]:
    """Extract text content from non-PDF documents using the unstructured lib."""

    try:
        from unstructured.partition.auto import partition  # type: ignore
    except Exception as exc:  # pragma: no cover - import/cfg issues
        message = f"Unstructured extractor unavailable: {exc}"
        logger.debug(message)
        return None, message

    try:
        elements = partition(filename=file_path)  # type: ignore[assignment]
    except Exception as exc:  # pragma: no cover - defensive
        message = f"Unstructured extractor failed: {exc}"
        logger.debug(message, exc_info=True)
        return None, message

    text_blocks = [
        el.text.strip()
        for el in elements
        if getattr(el, "text", None) and isinstance(getattr(el, "text"), str)
    ]

    if not text_blocks:
        message = "Unstructured extractor returned no text blocks"
        logger.debug("%s for %s", message, file_path)
        return None, message

    return "\n".join(text_blocks).strip(), None


__all__ = ["extract_pdf_text", "extract_unstructured_text"]
