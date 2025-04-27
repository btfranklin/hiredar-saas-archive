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
